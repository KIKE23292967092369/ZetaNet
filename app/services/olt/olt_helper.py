"""
Sistema ISP - OLT Helper
Funciones auxiliares para crear instancias de drivers OLT
a partir de los datos de olt_configs en la base de datos.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.olt import OltConfig
from app.models.cell import Cell
from app.services.olt.olt_base import OltCredentials, OltError, OnuInfo
from app.services.olt.olt_factory import get_olt_driver

logger = logging.getLogger("olt_helper")


async def get_olt_for_cell(db: AsyncSession, cell_id: int, tenant_id: int):
    """
    Obtiene un driver OLT configurado para la célula indicada.
    Lee los datos de olt_configs y crea el driver correcto.
    
    Args:
        db: Sesión de base de datos
        cell_id: ID de la célula
        tenant_id: ID del tenant
    
    Returns:
        Instancia del driver OLT (ZteDriver, VsolDriver, etc.)
    """
    # Buscar célula
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != tenant_id:
        raise OltError("Célula no encontrada")

    # Buscar configuración OLT de la célula
    result = await db.execute(
        select(OltConfig).where(
            OltConfig.cell_id == cell_id,
            OltConfig.tenant_id == tenant_id
        )
    )
    olt_config = result.scalar_one_or_none()

    if not olt_config:
        raise OltError(
            f"La célula '{cell.name}' no tiene OLT configurada. "
            f"Configure la OLT en la sección de células."
        )

    if not olt_config.hostname:
        raise OltError(
            f"La OLT de célula '{cell.name}' no tiene hostname/IP configurado."
        )

    if not olt_config.brand:
        raise OltError(
            f"La OLT de célula '{cell.name}' no tiene marca configurada. "
            f"Marcas soportadas: ZTE, VSOL."
        )

    # Crear credenciales
    credentials = OltCredentials(
        host=olt_config.hostname,
        ssh_port=olt_config.ssh_port or 22,
        ssh_username=olt_config.ssh_username or "admin",
        ssh_password=olt_config.ssh_password or "",
        snmp_port=olt_config.snmp_port or 161,
        snmp_community=olt_config.snmp_community or "public",
        brand=olt_config.brand,
        model=olt_config.model or ""
    )

    # Crear driver según marca
    return get_olt_driver(credentials)


async def authorize_onu_for_connection(
    db: AsyncSession,
    connection,
    serial_number: str,
    frame_slot_port: str,
    onu_type: str = "",
    line_profile: str = "",
    remote_profile: str = "",
    vlan: str = ""
) -> dict:
    """
    Autoriza una ONU en la OLT de la célula de la conexión.
    Se llama desde el endpoint authorize-onu.
    
    Returns:
        Dict con resultado de la autorización
    """
    try:
        driver = await get_olt_for_cell(db, connection.cell_id, connection.tenant_id)

        # Parsear frame/slot/port
        frame, slot, pon_port = driver.parse_frame_slot_port(frame_slot_port)

        result = await driver.authorize_onu(
            serial_number=serial_number,
            slot=slot,
            pon_port=pon_port,
            onu_type=onu_type,
            line_profile=line_profile,
            remote_profile=remote_profile,
            vlan=vlan,
            description=f"Conexión #{connection.id}"
        )

        logger.info(f"ONU {serial_number} autorizada para conexión {connection.id}")
        return {"olt_status": "authorized", "details": result}

    except OltError as e:
        logger.error(f"Error OLT al autorizar ONU para conexión {connection.id}: {e}")
        return {"olt_status": "error", "error": str(e)}


async def deauthorize_onu_for_connection(
    db: AsyncSession,
    connection
) -> dict:
    """
    Desautoriza una ONU al cancelar una conexión FIBRA.
    Lee slot/port/onu_id de los datos de autorización guardados.
    """
    try:
        if not connection.onu_auth_frame_slot_port:
            return {"olt_status": "skipped", "reason": "No hay datos de autorización ONU"}

        driver = await get_olt_for_cell(db, connection.cell_id, connection.tenant_id)

        frame, slot, pon_port = driver.parse_frame_slot_port(
            connection.onu_auth_frame_slot_port
        )

        # Necesitamos el onu_id - intentar obtenerlo
        # Por ahora usar el que se pueda parsear del frame_slot_port
        # TODO: Guardar onu_id en la conexión al autorizar
        result = await driver.deauthorize_onu(
            slot=slot,
            pon_port=pon_port,
            onu_id=1  # Placeholder - mejorar guardando onu_id en conexión
        )

        logger.info(f"ONU desautorizada para conexión {connection.id}")
        return {"olt_status": "deauthorized", "details": result}

    except OltError as e:
        logger.error(f"Error OLT al desautorizar ONU para conexión {connection.id}: {e}")
        return {"olt_status": "error", "error": str(e)}