"""
Sistema ISP - Router: Importar Clientes desde MikroTik
Lee PPPoE Secrets y Queues del MikroTik y crea Clientes + Conexiones.

Para ISPs que ya tienen clientes funcionando y quieren migrar a la plataforma.
NO toca el MikroTik (no crea ni modifica nada), solo REGISTRA lo que ya existe.

Endpoints:
  GET   /mikrotik/import/{cell_id}/preview   → Preview: qué se va a importar
  POST  /mikrotik/import/{cell_id}/execute   → Ejecutar importación
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.client import Client, ClientStatus
from app.models.cell import Cell
from app.models.connection import Connection, ConnectionType, ConnectionStatus
from app.services.mikrotik_service import MikroTikService, MikroTikError
from app.services.mikrotik_helper import get_mikrotik_for_cell

logger = logging.getLogger("mikrotik_import")

router = APIRouter(prefix="/mikrotik/import", tags=["Importar desde MikroTik"])


# ================================================================
# HELPER: Parsear datos del MikroTik
# ================================================================

def _parse_speed(max_limit: str) -> dict:
    """
    Parsea max-limit del MikroTik.
    Formato: "25M/50M" o "25000000/50000000" (upload/download)
    Retorna: {"upload": "25M", "download": "50M"}
    """
    if not max_limit:
        return {"upload": "0", "download": "0"}

    parts = max_limit.split("/")
    if len(parts) == 2:
        return {"upload": parts[0].strip(), "download": parts[1].strip()}
    return {"upload": max_limit, "download": max_limit}


def _extract_name_from_comment(comment: str, fallback: str) -> dict:
    """
    Intenta extraer nombre del comment del MikroTik.
    Muchos ISPs ponen el nombre del cliente en el comment.
    Retorna: {"first_name": str, "last_name": str}
    """
    if not comment:
        return {"first_name": fallback, "last_name": "(importado)"}

    # Limpiar prefijos comunes
    clean = comment
    for prefix in ["ISP-AUTO:", "Cliente:", "CLIENTE:", "cliente:"]:
        clean = clean.replace(prefix, "").strip()

    if not clean:
        return {"first_name": fallback, "last_name": "(importado)"}

    parts = clean.split(" ", 1)
    first_name = parts[0].strip()
    last_name = parts[1].strip() if len(parts) > 1 else "(importado)"

    return {"first_name": first_name, "last_name": last_name}


def _clean_target_ip(target: str) -> str:
    """
    Limpia el target de una queue.
    "10.10.10.5/32" → "10.10.10.5"
    """
    if not target:
        return ""
    return target.split("/")[0].strip()


async def _get_existing_connections(db: AsyncSession, tenant_id: int, cell_id: int) -> dict:
    """
    Obtiene conexiones ya registradas para evitar duplicados.
    Retorna dict con pppoe_usernames e ip_addresses existentes.
    """
    result = await db.execute(
        select(Connection).where(
            Connection.tenant_id == tenant_id,
            Connection.cell_id == cell_id,
        )
    )
    connections = result.scalars().all()

    existing_pppoe = set()
    existing_ips = set()

    for conn in connections:
        if conn.pppoe_username:
            existing_pppoe.add(conn.pppoe_username)
        if conn.ip_address:
            existing_ips.add(conn.ip_address)

    return {"pppoe_usernames": existing_pppoe, "ip_addresses": existing_ips}


# ================================================================
# PREVIEW: Ver qué se va a importar
# ================================================================

@router.get("/{cell_id}/preview")
async def import_preview(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Lee el MikroTik y muestra qué clientes se pueden importar.
    NO modifica nada, solo muestra un preview.

    Detecta:
    - PPPoE Secrets → clientes FIBRA
    - Queues sin PPPoE → clientes ANTENA
    - Conexiones ya existentes → se marcan como "ya importado"
    """
    # Verificar célula
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")

    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
    except Exception as e:
        raise HTTPException(502, f"Error conectando al MikroTik: {e}")

    # Obtener conexiones existentes
    existing = await _get_existing_connections(db, user.tenant_id, cell_id)

    # Leer PPPoE Secrets
    try:
        secrets = await mk.list_pppoe_secrets()
    except MikroTikError:
        secrets = []

    # Leer Queues
    try:
        queues = await mk._execute("/queue/simple")
    except MikroTikError:
        queues = []

    # Set de usernames PPPoE (para identificar queues que son ANTENA)
    pppoe_usernames = {s.get("name", "") for s in secrets}
    pppoe_ips = {s.get("remote-address", "") for s in secrets}

    # Mapear queues por target IP para cruzar con PPPoE
    queue_by_ip = {}
    queue_by_name = {}
    for q in queues:
        target_ip = _clean_target_ip(q.get("target", ""))
        if target_ip:
            queue_by_ip[target_ip] = q
        q_name = q.get("name", "")
        queue_by_name[q_name] = q

    # --- FIBRA (PPPoE) ---
    fiber_imports = []
    for s in secrets:
        username = s.get("name", "")
        ip = s.get("remote-address", "")
        profile = s.get("profile", "default")
        comment = s.get("comment", "")
        disabled = s.get("disabled", "false") == "true"

        # Buscar queue asociada
        speed = {"upload": "0", "download": "0"}
        queue_name = f"queue_{username}"
        queue = queue_by_name.get(queue_name) or queue_by_ip.get(ip)
        if queue:
            speed = _parse_speed(queue.get("max-limit", ""))

        # Verificar si ya existe
        already_imported = username in existing["pppoe_usernames"]

        names = _extract_name_from_comment(comment, username)

        fiber_imports.append({
            "type": "FIBER",
            "pppoe_username": username,
            "ip_address": ip,
            "profile": profile,
            "upload_speed": speed["upload"],
            "download_speed": speed["download"],
            "first_name": names["first_name"],
            "last_name": names["last_name"],
            "comment": comment,
            "disabled": disabled,
            "already_imported": already_imported,
        })

    # --- ANTENA (Queues sin PPPoE) ---
    antenna_imports = []
    for q in queues:
        q_name = q.get("name", "")
        target_ip = _clean_target_ip(q.get("target", ""))
        comment = q.get("comment", "")
        disabled = q.get("disabled", "false") == "true"

        if not target_ip:
            continue

        # Si la IP pertenece a un PPPoE, ya se importó como FIBRA
        if target_ip in pppoe_ips:
            continue

        # Si el nombre de la queue parece ser de un PPPoE, saltar
        for pppoe_name in pppoe_usernames:
            if pppoe_name in q_name:
                break
        else:
            # Es una queue standalone → ANTENA
            speed = _parse_speed(q.get("max-limit", ""))
            already_imported = target_ip in existing["ip_addresses"]
            names = _extract_name_from_comment(comment, q_name)

            antenna_imports.append({
                "type": "ANTENNA",
                "ip_address": target_ip,
                "queue_name": q_name,
                "upload_speed": speed["upload"],
                "download_speed": speed["download"],
                "first_name": names["first_name"],
                "last_name": names["last_name"],
                "comment": comment,
                "disabled": disabled,
                "already_imported": already_imported,
            })

    # Resumen
    total_fiber = len(fiber_imports)
    total_antenna = len(antenna_imports)
    new_fiber = len([f for f in fiber_imports if not f["already_imported"]])
    new_antenna = len([a for a in antenna_imports if not a["already_imported"]])

    return {
        "cell_id": cell_id,
        "cell_name": cell.name if hasattr(cell, 'name') else f"Célula #{cell_id}",
        "summary": {
            "total_found": total_fiber + total_antenna,
            "fiber_found": total_fiber,
            "antenna_found": total_antenna,
            "new_to_import": new_fiber + new_antenna,
            "already_imported": (total_fiber - new_fiber) + (total_antenna - new_antenna),
        },
        "fiber_clients": fiber_imports,
        "antenna_clients": antenna_imports,
    }


# ================================================================
# EXECUTE: Importar clientes
# ================================================================

@router.post("/{cell_id}/execute")
async def import_execute(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Ejecuta la importación de clientes desde el MikroTik.
    Crea Clientes + Conexiones en la BD.
    NO toca el MikroTik (todo ya está funcionando ahí).

    Flujo:
    1. Lee PPPoE Secrets → crea Cliente + Conexión FIBER
    2. Lee Queues standalone → crea Cliente + Conexión ANTENNA
    3. Salta los que ya están importados
    """
    # Verificar célula
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")

    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
    except Exception as e:
        raise HTTPException(502, f"Error conectando al MikroTik: {e}")

    existing = await _get_existing_connections(db, user.tenant_id, cell_id)

    # Leer datos del MikroTik
    try:
        secrets = await mk.list_pppoe_secrets()
    except MikroTikError:
        secrets = []

    try:
        queues = await mk._execute("/queue/simple")
    except MikroTikError:
        queues = []

    pppoe_usernames = {s.get("name", "") for s in secrets}
    pppoe_ips = {s.get("remote-address", "") for s in secrets}

    queue_by_ip = {}
    queue_by_name = {}
    for q in queues:
        target_ip = _clean_target_ip(q.get("target", ""))
        if target_ip:
            queue_by_ip[target_ip] = q
        queue_by_name[q.get("name", "")] = q

    imported = {"fiber": 0, "antenna": 0, "skipped": 0, "errors": []}

    # --- IMPORTAR FIBRA ---
    for s in secrets:
        username = s.get("name", "")
        ip = s.get("remote-address", "")
        profile = s.get("profile", "default")
        comment = s.get("comment", "")
        disabled = s.get("disabled", "false") == "true"

        if username in existing["pppoe_usernames"]:
            imported["skipped"] += 1
            continue

        try:
            # Velocidad desde queue
            speed = {"upload": "0", "download": "0"}
            queue = queue_by_name.get(f"queue_{username}") or queue_by_ip.get(ip)
            if queue:
                speed = _parse_speed(queue.get("max-limit", ""))

            names = _extract_name_from_comment(comment, username)

            # Crear cliente
            client = Client(
                tenant_id=user.tenant_id,
                first_name=names["first_name"],
                last_name=names["last_name"],
                address="Pendiente - Importado desde MikroTik",
                phone_cell="",
                status=ClientStatus.ACTIVE,
            )
            db.add(client)
            await db.flush()

            # Crear conexión
            conn_status = ConnectionStatus.SUSPENDED if disabled else ConnectionStatus.ACTIVE

            connection = Connection(
                tenant_id=user.tenant_id,
                client_id=client.id,
                cell_id=cell_id,
                connection_type=ConnectionType.FIBER,
                status=conn_status,
                pppoe_username=username,
                ip_address=ip,
                onu_authorized=True,
            )
            db.add(connection)

            imported["fiber"] += 1
            existing["pppoe_usernames"].add(username)

        except Exception as e:
            imported["errors"].append(f"FIBER {username}: {str(e)}")
            logger.error(f"Error importando FIBER {username}: {e}")

    # --- IMPORTAR ANTENA ---
    for q in queues:
        q_name = q.get("name", "")
        target_ip = _clean_target_ip(q.get("target", ""))
        comment = q.get("comment", "")
        disabled = q.get("disabled", "false") == "true"

        if not target_ip:
            continue

        # Saltar si es de un PPPoE
        if target_ip in pppoe_ips:
            continue

        is_pppoe_queue = False
        for pppoe_name in pppoe_usernames:
            if pppoe_name in q_name:
                is_pppoe_queue = True
                break

        if is_pppoe_queue:
            continue

        if target_ip in existing["ip_addresses"]:
            imported["skipped"] += 1
            continue

        try:
            speed = _parse_speed(q.get("max-limit", ""))
            names = _extract_name_from_comment(comment, q_name)

            # Crear cliente
            client = Client(
                tenant_id=user.tenant_id,
                first_name=names["first_name"],
                last_name=names["last_name"],
                address="Pendiente - Importado desde MikroTik",
                phone_cell="",
                status=ClientStatus.ACTIVE,
            )
            db.add(client)
            await db.flush()

            # Crear conexión
            conn_status = ConnectionStatus.SUSPENDED if disabled else ConnectionStatus.ACTIVE

            connection = Connection(
                tenant_id=user.tenant_id,
                client_id=client.id,
                cell_id=cell_id,
                connection_type=ConnectionType.ANTENNA,
                status=conn_status,
                ip_address=target_ip,
            )
            db.add(connection)

            imported["antenna"] += 1
            existing["ip_addresses"].add(target_ip)

        except Exception as e:
            imported["errors"].append(f"ANTENNA {target_ip}: {str(e)}")
            logger.error(f"Error importando ANTENNA {target_ip}: {e}")

    # Commit todo
    await db.commit()

    total_imported = imported["fiber"] + imported["antenna"]
    return {
        "message": f"Importación completada: {total_imported} clientes importados",
        "cell_id": cell_id,
        "results": {
            "fiber_imported": imported["fiber"],
            "antenna_imported": imported["antenna"],
            "total_imported": total_imported,
            "skipped_existing": imported["skipped"],
            "errors": imported["errors"],
            "error_count": len(imported["errors"]),
        }
    }