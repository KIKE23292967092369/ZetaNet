"""
Sistema ISP - Router: Conexiones (CON integración MikroTik)
Crear FIBRA (cascada) y ANTENA (directo).
Validación MAC única. Autorización ONU.

INTEGRACIÓN MIKROTIK:
- Al crear FIBRA → crea PPPoE Secret + Queue en MikroTik
- Al crear ANTENA → crea Queue + Address List en MikroTik
- Al cancelar → elimina configuración del MikroTik
- Al cambiar status → suspende/reactiva en MikroTik
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
import logging

from app.dependencies import get_db, get_current_user
from app.models.connection import Connection, ConnectionType, ConnectionStatus
from app.models.cell import Cell, CellType
from app.models.network import NapPort
from app.models.inventory import Onu, Cpe, Router
from app.models.plan import ServicePlan, CellPlan
from app.models.client import Client
from app.models.user import User
from app.schemas.connection import (
    ConnectionFiberCreate, ConnectionAntennaCreate,
    AuthorizeOnuRequest, ConnectionUpdate, ConnectionCancelRequest,
    ConnectionResponse, ConnectionListResponse
)
from app.schemas.common import MessageResponse

# MikroTik integration
from app.services.mikrotik_helper import (
    provision_fiber_from_connection,
    provision_antenna_from_connection,
    deprovision_connection,
    suspend_connection_mikrotik,
    reactivate_connection_mikrotik
)

logger = logging.getLogger("connections_router")

router = APIRouter(prefix="/connections", tags=["Conexiones"])


# ========== HELPERS ==========

async def validate_mac_unique(db: AsyncSession, tenant_id: int, mac: str, table, field, exclude_id: int = None):
    """Valida que una MAC no esté duplicada en el tenant."""
    q = select(table).where(
        table.tenant_id == tenant_id,
        getattr(table, field) == mac.upper()
    )
    if exclude_id:
        q = q.where(table.id != exclude_id)
    result = await db.execute(q)
    existing = result.scalar_one_or_none()
    if existing:
        conn_info = f" - asignado a conexión {existing.connection_id}" if existing.connection_id else ""
        raise HTTPException(
            400,
            f"MAC {mac} ya está registrada (ID: {existing.id}){conn_info}"
        )


async def validate_equipment_available(db: AsyncSession, tenant_id: int, model, equip_id: int, label: str):
    """Valida que un equipo (ONU/CPE/Router) esté disponible."""
    equip = await db.get(model, equip_id)
    if not equip or equip.tenant_id != tenant_id:
        raise HTTPException(404, f"{label} no encontrado(a)")
    if not equip.is_active:
        raise HTTPException(400, f"{label} no está activo(a)")
    if equip.connection_id:
        raise HTTPException(400, f"{label} ya está asignado(a) a conexión {equip.connection_id}")
    return equip


async def validate_plan_in_cell(db: AsyncSession, tenant_id: int, plan_id: int, cell_id: int):
    """Valida que el plan esté asignado a la célula."""
    result = await db.execute(
        select(CellPlan).where(
            CellPlan.tenant_id == tenant_id,
            CellPlan.cell_id == cell_id,
            CellPlan.plan_id == plan_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(400, "El plan no está asignado a esta célula")


# ========== LISTAR ==========

@router.get("/", response_model=List[ConnectionListResponse])
async def list_connections(
    cell_id: Optional[int] = None,
    client_id: Optional[int] = None,
    connection_type: Optional[ConnectionType] = None,
    status: Optional[ConnectionStatus] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = (
        select(
            Connection,
            Client.first_name,
            Client.last_name,
            ServicePlan.name.label("plan_name"),
            Cell.name.label("cell_name")
        )
        .join(Client, Connection.client_id == Client.id, isouter=True)
        .join(ServicePlan, Connection.plan_id == ServicePlan.id, isouter=True)
        .join(Cell, Connection.cell_id == Cell.id, isouter=True)
        .where(Connection.tenant_id == user.tenant_id, Connection.is_active == True)
    )

    if cell_id:
        q = q.where(Connection.cell_id == cell_id)
    if client_id:
        q = q.where(Connection.client_id == client_id)
    if connection_type:
        q = q.where(Connection.connection_type == connection_type)
    if status:
        q = q.where(Connection.status == status)

    q = q.order_by(Connection.id.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    rows = result.all()

    return [
        ConnectionListResponse(
            id=conn.id,
            client_id=conn.client_id,
            client_name=f"{fname or ''} {lname or ''}".strip(),
            connection_type=conn.connection_type,
            status=conn.status,
            ip_address=conn.ip_address,
            plan_name=pname or "",
            cell_name=cname or "",
            created_at=conn.created_at
        )
        for conn, fname, lname, pname, cname in rows
    ]


# ========== CREAR FIBRA ==========

@router.post("/fiber", response_model=ConnectionResponse, status_code=201)
async def create_fiber_connection(
    data: ConnectionFiberCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Crear conexión FIBRA (PPPoE).
    Cascada: Célula → Zona OLT → NAP → Puerto → IP → PPPoE → ONU
    Al guardar: se crea PPP Secret + Queue en MikroTik automáticamente.
    Falta autorizar ONU en la OLT.
    """
    tid = user.tenant_id

    # Validar célula es FIBRA
    cell = await db.get(Cell, data.cell_id)
    if not cell or cell.tenant_id != tid:
        raise HTTPException(404, "Célula no encontrada")
    if cell.cell_type != CellType.FIBRA:
        raise HTTPException(400, "La célula no es de tipo FIBRA")

    # Validar cliente
    client = await db.get(Client, data.client_id)
    if not client or client.tenant_id != tid:
        raise HTTPException(404, "Cliente no encontrado")

    # Validar plan asignado a célula
    await validate_plan_in_cell(db, tid, data.plan_id, data.cell_id)

    # Obtener plan para velocidades
    plan = await db.get(ServicePlan, data.plan_id)

    # Validar puerto NAP libre
    port = await db.get(NapPort, data.nap_port_id)
    if not port or port.tenant_id != tid:
        raise HTTPException(404, "Puerto NAP no encontrado")
    if port.is_occupied:
        raise HTTPException(400, f"Puerto {port.port_number} ya está ocupado")

    # Validar ONU disponible
    onu = await validate_equipment_available(db, tid, Onu, data.onu_id, "ONU")

    # Crear conexión
    conn = Connection(
        tenant_id=tid,
        connection_type=ConnectionType.FIBER,
        status=ConnectionStatus.PENDING_AUTH,
        **data.model_dump()
    )
    db.add(conn)
    await db.flush()

    # Marcar puerto como ocupado
    port.is_occupied = True
    port.connection_id = conn.id

    # Marcar ONU como asignada
    onu.connection_id = conn.id

    # ===== MIKROTIK: Crear PPPoE Secret + Queue =====
    mk_result = await provision_fiber_from_connection(db, conn, plan)
    if mk_result.get("mikrotik_status") == "error":
        logger.warning(
            f"MikroTik no disponible para conexión {conn.id}: {mk_result.get('error')}. "
            f"La conexión se creó en BD pero NO en el router."
        )
    # ================================================

    await db.commit()
    await db.refresh(conn)
    return conn


# ========== CREAR ANTENA ==========

@router.post("/antenna", response_model=ConnectionResponse, status_code=201)
async def create_antenna_connection(
    data: ConnectionAntennaCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Crear conexión ANTENA (IP Estática).
    Flujo directo: Célula → IP + MAC → CPE → internet inmediato.
    Se crea Queue + Address List en MikroTik automáticamente.
    """
    tid = user.tenant_id

    # Validar célula es ANTENAS
    cell = await db.get(Cell, data.cell_id)
    if not cell or cell.tenant_id != tid:
        raise HTTPException(404, "Célula no encontrada")
    if cell.cell_type != CellType.ANTENAS:
        raise HTTPException(400, "La célula no es de tipo ANTENAS")

    # Validar cliente
    client = await db.get(Client, data.client_id)
    if not client or client.tenant_id != tid:
        raise HTTPException(404, "Cliente no encontrado")

    # Validar plan asignado a célula
    await validate_plan_in_cell(db, tid, data.plan_id, data.cell_id)

    # Obtener plan para velocidades
    plan = await db.get(ServicePlan, data.plan_id)

    # Validar CPE disponible
    cpe = await validate_equipment_available(db, tid, Cpe, data.cpe_id, "CPE")

    # Validar Router si se envía
    if data.router_id:
        await validate_equipment_available(db, tid, Router, data.router_id, "Router")

    # Crear conexión
    conn = Connection(
        tenant_id=tid,
        connection_type=ConnectionType.ANTENNA,
        status=ConnectionStatus.ACTIVE,
        **data.model_dump()
    )
    db.add(conn)
    await db.flush()

    # Marcar CPE como asignado
    cpe.connection_id = conn.id

    # Marcar Router si aplica
    if data.router_id:
        rtr = await db.get(Router, data.router_id)
        if rtr:
            rtr.connection_id = conn.id

    # ===== MIKROTIK: Crear Queue + Address List =====
    mk_result = await provision_antenna_from_connection(db, conn, plan)
    if mk_result.get("mikrotik_status") == "error":
        logger.warning(
            f"MikroTik no disponible para conexión {conn.id}: {mk_result.get('error')}. "
            f"La conexión se creó en BD pero NO en el router."
        )
    # ================================================

    await db.commit()
    await db.refresh(conn)
    return conn


# ========== AUTORIZAR ONU (FIBRA) ==========

@router.post("/authorize-onu", response_model=ConnectionResponse)
async def authorize_onu(
    data: AuthorizeOnuRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Autorizar ONU en la OLT.
    Se selecciona Frame/Slot/Puerto, Line profile, Remote profile, VLAN.
    Se envía comando SSH a la OLT → PON deja de parpadear → internet.
    """
    conn = await db.get(Connection, data.connection_id)
    if not conn or conn.tenant_id != user.tenant_id:
        raise HTTPException(404, "Conexión no encontrada")
    if conn.connection_type != ConnectionType.FIBER:
        raise HTTPException(400, "Solo conexiones FIBRA requieren autorización")
    if conn.onu_authorized:
        raise HTTPException(400, "ONU ya está autorizada")

    # Guardar datos de autorización
    conn.onu_authorized = True
    conn.onu_auth_frame_slot_port = data.frame_slot_port
    conn.onu_auth_line_profile = data.line_profile
    conn.onu_auth_remote_profile = data.remote_profile
    conn.onu_auth_vlan = data.vlan
    conn.status = ConnectionStatus.ACTIVE

    # TODO PASO 3: Enviar comando SSH a la OLT para registrar ONU
    # Esto se implementa en el Paso 3 (OLT multi-marca SSH/SNMP)
    # Ejemplo ZTE: onu add sn {serial} lineprofile {lp} remoteprofile {rp} vlan {v}

    await db.commit()
    await db.refresh(conn)
    return conn


# ========== DETALLE ==========

@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    conn = await db.get(Connection, connection_id)
    if not conn or conn.tenant_id != user.tenant_id:
        raise HTTPException(404, "Conexión no encontrada")
    return conn


# ========== ACTUALIZAR ==========

@router.patch("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: int,
    data: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    conn = await db.get(Connection, connection_id)
    if not conn or conn.tenant_id != user.tenant_id:
        raise HTTPException(404, "Conexión no encontrada")

    old_status = conn.status

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(conn, k, v)

    # ===== MIKROTIK: Suspender / Reactivar según cambio de status =====
    new_status = conn.status
    if old_status != new_status:
        if new_status == ConnectionStatus.SUSPENDED:
            mk_result = await suspend_connection_mikrotik(db, conn)
            logger.info(f"Conexión {conn.id} suspendida en MikroTik: {mk_result}")
        elif new_status == ConnectionStatus.ACTIVE and old_status == ConnectionStatus.SUSPENDED:
            mk_result = await reactivate_connection_mikrotik(db, conn)
            logger.info(f"Conexión {conn.id} reactivada en MikroTik: {mk_result}")
    # ==================================================================

    await db.commit()
    await db.refresh(conn)
    return conn


# ========== ELIMINAR (BAJA) ==========

@router.post("/{connection_id}/cancel", response_model=MessageResponse)
async def cancel_connection(
    connection_id: int,
    data: ConnectionCancelRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Dar de baja una conexión.
    Libera ONU/CPE/Router y puerto NAP.
    Elimina PPPoE Secret y Queue del MikroTik.
    """
    conn = await db.get(Connection, connection_id)
    if not conn or conn.tenant_id != user.tenant_id:
        raise HTTPException(404, "Conexión no encontrada")

    # ===== MIKROTIK: Eliminar configuración del router =====
    mk_result = await deprovision_connection(db, conn)
    if mk_result.get("mikrotik_status") == "error":
        logger.warning(
            f"No se pudo eliminar del MikroTik conexión {conn.id}: {mk_result.get('error')}. "
            f"Se continúa con la baja en BD."
        )
    # =======================================================

    conn.status = ConnectionStatus.CANCELLED
    conn.cancel_reason = data.cancel_reason
    conn.cancel_detail = data.cancel_detail
    conn.is_active = False

    # Liberar puerto NAP
    if conn.nap_port_id:
        port = await db.get(NapPort, conn.nap_port_id)
        if port:
            port.is_occupied = False
            port.connection_id = None

    # Liberar ONU
    if conn.onu_id:
        onu = await db.get(Onu, conn.onu_id)
        if onu:
            onu.connection_id = None

    # Liberar CPE
    if conn.cpe_id:
        cpe = await db.get(Cpe, conn.cpe_id)
        if cpe:
            cpe.connection_id = None

    # Liberar Router
    if conn.router_id:
        rtr = await db.get(Router, conn.router_id)
        if rtr:
            rtr.connection_id = None

    await db.commit()
    return MessageResponse(
        message="Conexión dada de baja",
        detail=f"Motivo: {data.cancel_reason.value}"
    )