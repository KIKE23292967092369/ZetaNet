"""
Sistema ISP - MikroTik Helper
Funciones auxiliares para crear instancias del servicio MikroTik
a partir de los datos de células en la base de datos.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.cell import Cell
from app.services.mikrotik_service import MikroTikService, MikroTikError

logger = logging.getLogger("mikrotik_helper")


async def get_mikrotik_for_cell(db: AsyncSession, cell_id: int, tenant_id: int) -> MikroTikService:
    """
    Obtiene una instancia de MikroTikService configurada
    con las credenciales del MikroTik asociado a una célula.
    
    Args:
        db: Sesión de base de datos
        cell_id: ID de la célula
        tenant_id: ID del tenant
    
    Returns:
        MikroTikService configurado y listo para usar
    
    Raises:
        MikroTikError: Si la célula no tiene MikroTik configurado
    """
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != tenant_id:
        raise MikroTikError("Célula no encontrada")

    if not cell.mikrotik_host:
        raise MikroTikError(
            f"La célula '{cell.name}' no tiene MikroTik configurado. "
            f"Configure host, puerto y credenciales en la célula."
        )

    return MikroTikService(
        host=cell.mikrotik_host,
        port=cell.mikrotik_api_port or 8728,
        username=cell.mikrotik_username_encrypted or "admin",
        password=cell.mikrotik_password_encrypted or ""
    )


async def provision_fiber_from_connection(db: AsyncSession, connection, plan) -> dict:
    """
    Provisiona una conexión FIBRA en el MikroTik de su célula.
    
    Crea PPPoE Secret + Queue automáticamente.
    Si el MikroTik no está disponible, registra el error pero no bloquea.
    
    Returns:
        Dict con resultado de la operación MikroTik
    """
    try:
        mk = await get_mikrotik_for_cell(db, connection.cell_id, connection.tenant_id)
        
        # Obtener nombre del cliente para el comentario
        from app.models.client import Client
        client = await db.get(Client, connection.client_id)
        client_name = f"{client.first_name} {client.last_name}" if client else ""

        result = await mk.provision_fiber_client(
            pppoe_username=connection.pppoe_username,
            pppoe_password=connection.pppoe_password_encrypted,
            ip_address=connection.ip_address or "",
            upload_speed=plan.upload_speed or "10M",
            download_speed=plan.download_speed or "10M",
            profile=connection.pppoe_profile or "default",
            client_name=client_name,
            burst_upload=plan.burst_limit_upload or "",
            burst_download=plan.burst_limit_download or "",
            burst_threshold_up=plan.burst_threshold_upload or "",
            burst_threshold_down=plan.burst_threshold_download or "",
            burst_time=plan.burst_time_upload or ""
        )

        logger.info(f"MikroTik FIBRA provisionado para conexión {connection.id}")
        return {"mikrotik_status": "provisioned", "details": result}

    except MikroTikError as e:
        logger.error(f"Error MikroTik al provisionar FIBRA conexión {connection.id}: {e}")
        return {"mikrotik_status": "error", "error": str(e)}


async def provision_antenna_from_connection(db: AsyncSession, connection, plan) -> dict:
    """
    Provisiona una conexión ANTENA en el MikroTik de su célula.
    
    Crea Queue + Address-list automáticamente.
    """
    try:
        mk = await get_mikrotik_for_cell(db, connection.cell_id, connection.tenant_id)

        from app.models.client import Client
        client = await db.get(Client, connection.client_id)
        client_name = f"{client.first_name} {client.last_name}" if client else ""

        result = await mk.provision_antenna_client(
            ip_address=connection.ip_address or "",
            upload_speed=plan.upload_speed or "10M",
            download_speed=plan.download_speed or "10M",
            client_name=client_name,
            burst_upload=plan.burst_limit_upload or "",
            burst_download=plan.burst_limit_download or "",
            burst_threshold_up=plan.burst_threshold_upload or "",
            burst_threshold_down=plan.burst_threshold_download or "",
            burst_time=plan.burst_time_upload or ""
        )

        logger.info(f"MikroTik ANTENA provisionado para conexión {connection.id}")
        return {"mikrotik_status": "provisioned", "details": result}

    except MikroTikError as e:
        logger.error(f"Error MikroTik al provisionar ANTENA conexión {connection.id}: {e}")
        return {"mikrotik_status": "error", "error": str(e)}


async def deprovision_connection(db: AsyncSession, connection) -> dict:
    """
    Elimina la configuración de una conexión del MikroTik.
    Se usa al cancelar/dar de baja una conexión.
    """
    try:
        mk = await get_mikrotik_for_cell(db, connection.cell_id, connection.tenant_id)

        if connection.connection_type.value == "fiber":
            result = await mk.deprovision_fiber_client(
                pppoe_username=connection.pppoe_username or "",
                ip_address=connection.ip_address or ""
            )
        else:
            result = await mk.deprovision_antenna_client(
                ip_address=connection.ip_address or ""
            )

        logger.info(f"MikroTik deprovisionado para conexión {connection.id}")
        return {"mikrotik_status": "deprovisioned", "details": result}

    except MikroTikError as e:
        logger.error(f"Error MikroTik al deprovisionar conexión {connection.id}: {e}")
        return {"mikrotik_status": "error", "error": str(e)}


async def suspend_connection_mikrotik(db: AsyncSession, connection) -> dict:
    """Suspende una conexión en el MikroTik."""
    try:
        mk = await get_mikrotik_for_cell(db, connection.cell_id, connection.tenant_id)

        result = await mk.suspend_client(
            pppoe_username=connection.pppoe_username,
            ip_address=connection.ip_address,
            connection_type=connection.connection_type.value
        )

        logger.info(f"Conexión {connection.id} suspendida en MikroTik")
        return {"mikrotik_status": "suspended", "details": result}

    except MikroTikError as e:
        logger.error(f"Error MikroTik al suspender conexión {connection.id}: {e}")
        return {"mikrotik_status": "error", "error": str(e)}


async def reactivate_connection_mikrotik(db: AsyncSession, connection) -> dict:
    """Reactiva una conexión suspendida en el MikroTik."""
    try:
        mk = await get_mikrotik_for_cell(db, connection.cell_id, connection.tenant_id)

        result = await mk.reactivate_client(
            pppoe_username=connection.pppoe_username,
            ip_address=connection.ip_address,
            connection_type=connection.connection_type.value
        )

        logger.info(f"Conexión {connection.id} reactivada en MikroTik")
        return {"mikrotik_status": "reactivated", "details": result}

    except MikroTikError as e:
        logger.error(f"Error MikroTik al reactivar conexión {connection.id}: {e}")
        return {"mikrotik_status": "error", "error": str(e)}