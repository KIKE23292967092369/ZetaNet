"""
Sistema ISP - Router: Diagnóstico de Conexión
Endpoints para ver potencia ONU, estado y consumo en tiempo real.
Se integra con OLT (SSH) y MikroTik (API 8728).

Endpoints:
  GET /connections/{id}/onu-review  → Revisar ONU (potencia, señal, estado)
  GET /connections/{id}/realtime    → Consumo tiempo real (descarga/subida)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.connection import Connection, ConnectionType
from app.services.olt.olt_base import OltError
from app.services.olt.olt_helper import get_olt_for_cell

router = APIRouter(prefix="/connections", tags=["Diagnóstico Conexión"])


# ================================================================
# HELPER: Obtener conexión validada
# ================================================================

async def _get_connection(
    connection_id: int,
    tenant_id: int,
    db: AsyncSession
) -> Connection:
    """Obtiene una conexión verificando tenant y que exista."""
    result = await db.execute(
        select(Connection)
        .options(selectinload(Connection.onu), selectinload(Connection.client))
        .where(
            Connection.id == connection_id,
            Connection.tenant_id == tenant_id
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(404, "Conexión no encontrada")
    return conn


# ================================================================
# REVISAR ONU (Potencia + Estado + Señal)
# ================================================================

@router.get("/{connection_id}/onu-review")
async def review_onu(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Revisar ONU de una conexión FIBRA.
    Consulta la OLT en tiempo real y retorna:
    - Estado: online/offline
    - Rx Power (potencia del módem del cliente)
    - Tx Power (potencia de transmisión)
    - Señal: excelente/buena/aceptable/baja/critica
    - Distancia en metros
    - Temperatura
    
    Solo funciona en conexiones FIBRA con ONU autorizada.
    """
    conn = await _get_connection(connection_id, user.tenant_id, db)

    # Validaciones
    if conn.connection_type != ConnectionType.FIBER:
        raise HTTPException(400, "Solo conexiones FIBRA tienen ONU")

    if not conn.onu_authorized:
        raise HTTPException(400, "La ONU de esta conexión aún no está autorizada")

    if not conn.onu_auth_frame_slot_port:
        raise HTTPException(400, "No hay datos de frame/slot/puerto para esta ONU")

    if not conn.onu_auth_olt_id:
        raise HTTPException(
            400,
            "No se tiene el ID de ONU en la OLT. "
            "Reautorice la ONU para guardar este dato."
        )

    # Obtener driver OLT
    try:
        driver = await get_olt_for_cell(db, conn.cell_id, user.tenant_id)
    except OltError as e:
        raise HTTPException(502, f"Error conectando a OLT: {e}")

    # Parsear frame/slot/port
    try:
        frame, slot, pon_port = driver.parse_frame_slot_port(conn.onu_auth_frame_slot_port)
    except OltError as e:
        raise HTTPException(400, f"Formato frame/slot/port inválido: {e}")

    olt_onu_id = conn.onu_auth_olt_id

    # Consultar estado y óptica en paralelo
    status_data = {}
    optical_data = {}
    errors = []

    # Estado (online/offline)
    try:
        onu_status = await driver.get_onu_status(
            slot=slot, pon_port=pon_port, onu_id=olt_onu_id
        )
        status_data = {
            "status": onu_status.status,
            "serial_number": onu_status.serial_number,
            "model": onu_status.model,
            "distance": onu_status.distance,
        }
    except OltError as e:
        errors.append(f"Error leyendo estado: {e}")

    # Óptica (potencia, temperatura)
    try:
        optical = await driver.get_onu_optical_info(
            slot=slot, pon_port=pon_port, onu_id=olt_onu_id
        )
        optical_data = optical

        # Evaluar calidad de señal
        rx = optical.get("rx_power")
        if rx is not None:
            if rx >= -8:
                optical_data["signal_quality"] = "excelente"
                optical_data["signal_color"] = "green"
            elif rx >= -15:
                optical_data["signal_quality"] = "buena"
                optical_data["signal_color"] = "green"
            elif rx >= -23:
                optical_data["signal_quality"] = "aceptable"
                optical_data["signal_color"] = "yellow"
            elif rx >= -25:
                optical_data["signal_quality"] = "baja"
                optical_data["signal_color"] = "orange"
            else:
                optical_data["signal_quality"] = "critica"
                optical_data["signal_color"] = "red"
    except OltError as e:
        errors.append(f"Error leyendo óptica: {e}")

    # Info del cliente y ONU del inventario
    client_name = ""
    if conn.client:
        client_name = f"{conn.client.first_name} {conn.client.last_name}"

    onu_info = {}
    if conn.onu:
        onu_info = {
            "inventory_id": conn.onu.id,
            "mac_address": getattr(conn.onu, "mac_address", None),
            "brand": getattr(conn.onu, "brand_name", None),
            "model": getattr(conn.onu, "model_name", None),
        }

    return {
        "connection_id": conn.id,
        "client_name": client_name,
        "connection_type": "fiber",
        "ip_address": conn.ip_address,
        "frame_slot_port": conn.onu_auth_frame_slot_port,
        "olt_onu_id": olt_onu_id,
        "line_profile": conn.onu_auth_line_profile,
        "remote_profile": conn.onu_auth_remote_profile,
        "vlan": conn.onu_auth_vlan,
        "onu_inventory": onu_info,
        **status_data,
        **optical_data,
        "errors": errors if errors else None,
    }


# ================================================================
# CONSUMO TIEMPO REAL (MikroTik)
# ================================================================

@router.get("/{connection_id}/realtime")
async def realtime_consumption(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Consumo en tiempo real de una conexión.
    Lee el queue del MikroTik para obtener descarga/subida actual.
    
    Funciona para FIBRA (PPPoE) y ANTENA (IP estática).
    Retorna: velocidad actual en kbps (descarga/subida).
    """
    conn = await _get_connection(connection_id, user.tenant_id, db)

    if not conn.is_active:
        raise HTTPException(400, "La conexión está inactiva")

    # Necesitamos el MikroTik de la célula
    # Importar aquí para evitar circular imports
    from app.services.mikrotik_service import MikroTikService

    try:
        mk_service = await MikroTikService.from_cell(db, conn.cell_id, user.tenant_id)
    except Exception as e:
        raise HTTPException(502, f"Error conectando a MikroTik: {e}")

    # Buscar el queue de esta conexión
    # FIBRA: el queue se identifica por el usuario PPPoE
    # ANTENA: el queue se identifica por la IP
    try:
        if conn.connection_type == ConnectionType.FIBER:
            # Buscar por nombre de queue (usualmente el usuario PPPoE)
            target = conn.pppoe_username
            if not target:
                raise HTTPException(400, "Conexión FIBRA sin usuario PPPoE configurado")
        else:
            # ANTENA: buscar por IP
            target = conn.ip_address
            if not target:
                raise HTTPException(400, "Conexión ANTENA sin IP configurada")

        # Leer queues del MikroTik
        queues = await mk_service.get_queues()

        # Buscar el queue que corresponde a esta conexión
        connection_queue = None
        for q in queues:
            q_name = q.get("name", "")
            q_target = q.get("target", "")

            if conn.connection_type == ConnectionType.FIBER:
                # PPPoE: el queue name suele ser el username
                if target.lower() in q_name.lower():
                    connection_queue = q
                    break
            else:
                # ANTENA: buscar por IP en target
                if target in q_target:
                    connection_queue = q
                    break

        if not connection_queue:
            return {
                "connection_id": conn.id,
                "status": "no_queue",
                "message": f"No se encontró queue para '{target}' en MikroTik",
                "download_kbps": 0,
                "upload_kbps": 0,
            }

        # Extraer datos de consumo
        # rate format en MikroTik: "upload/download" en bytes
        rate = connection_queue.get("rate", "0/0")
        rates = rate.split("/") if "/" in str(rate) else ["0", "0"]

        upload_bytes = int(rates[0]) if rates[0].isdigit() else 0
        download_bytes = int(rates[1]) if len(rates) > 1 and rates[1].isdigit() else 0

        # Convertir a kbps
        upload_kbps = round(upload_bytes * 8 / 1024, 2)
        download_kbps = round(download_bytes * 8 / 1024, 2)

        # Info del plan
        max_limit = connection_queue.get("max-limit", "")

        # Info del cliente
        client_name = ""
        if conn.client:
            client_name = f"{conn.client.first_name} {conn.client.last_name}"

        return {
            "connection_id": conn.id,
            "client_name": client_name,
            "connection_type": conn.connection_type.value,
            "ip_address": conn.ip_address,
            "target": target,
            "status": "active",
            "queue_name": connection_queue.get("name", ""),
            "download_kbps": download_kbps,
            "upload_kbps": upload_kbps,
            "download_bytes": download_bytes,
            "upload_bytes": upload_bytes,
            "max_limit": max_limit,
            "disabled": connection_queue.get("disabled", "false"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Error leyendo MikroTik: {e}")