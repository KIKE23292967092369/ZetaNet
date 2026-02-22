"""
Sistema ISP - Router: OLT Management
Endpoints para gestionar OLTs desde la plataforma.
Test de conexión, listar ONUs, autorizar, ver señal, etc.
Soporta múltiples marcas (ZTE, VSOL) con driver automático.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.olt.olt_base import OltCredentials, OltError
from app.services.olt.olt_helper import get_olt_for_cell
from app.services.olt.olt_factory import get_olt_driver, get_supported_brands

router = APIRouter(prefix="/olt", tags=["OLT"])


# ================================================================
# SCHEMAS
# ================================================================

class DirectConnectRequest(BaseModel):
    """Request para conectar a una OLT directamente con credenciales."""
    host: str
    ssh_username: str
    ssh_password: str
    ssh_port: int = 22
    brand: str  # "zte", "vsol", etc.


class AuthorizeOnuOltRequest(BaseModel):
    """Request para autorizar ONU directamente en la OLT."""
    cell_id: int
    serial_number: str
    slot: int
    pon_port: int
    onu_id: Optional[int] = None
    onu_type: str = ""
    line_profile: str = ""
    remote_profile: str = ""
    vlan: str = "100"
    description: str = ""


class DeauthorizeOnuOltRequest(BaseModel):
    """Request para eliminar ONU de la OLT."""
    cell_id: int
    slot: int
    pon_port: int
    onu_id: int


class ConfigureServiceRequest(BaseModel):
    """Request para configurar VLAN de servicio en ONU."""
    cell_id: int
    slot: int
    pon_port: int
    onu_id: int
    vlan: str = "100"
    service_port: int = 1


class ExecuteCommandRequest(BaseModel):
    """Request para ejecutar comando SSH raw."""
    cell_id: int
    command: str
    timeout: int = 30


# ================================================================
# INFO
# ================================================================

@router.get("/supported-brands")
async def list_supported_brands():
    """Lista las marcas de OLT soportadas por el sistema."""
    return {
        "brands": get_supported_brands(),
        "note": "La marca se configura en la OLT de cada célula"
    }


# ================================================================
# CONEXIÓN DIRECTA — para Nodos de Red (sin cell_id)
# ================================================================

@router.post("/connect-direct")
async def connect_olt_direct(
    data: DirectConnectRequest,
    user: User = Depends(get_current_user)
):
    """
    Conecta a una OLT directamente con credenciales SSH.
    No requiere cell_id — usado en Nodos de Red para probar/monitorear.
    Retorna: estado de conexión, info del equipo, ONUs no autorizadas.
    """
    try:
        credentials = OltCredentials(
            host=data.host,
            ssh_username=data.ssh_username,
            ssh_password=data.ssh_password,
            ssh_port=data.ssh_port,
            brand=data.brand,
        )
        driver = get_olt_driver(credentials)
        result = await driver.test_connection()

        # Si conectó, traer ONUs no autorizadas
        unauthorized = []
        if result.get("connected"):
            try:
                onus = await driver.list_unauthorized_onus()
                unauthorized = [
                    {
                        "serial_number": onu.serial_number,
                        "slot": onu.slot,
                        "pon_port": onu.pon_port,
                        "model": onu.model,
                        "status": onu.status,
                    }
                    for onu in onus
                ]
            except Exception:
                pass  # ONUs no críticas, no bloquear respuesta

        return {
            **result,
            "host": data.host,
            "brand": data.brand,
            "unauthorized_onus": unauthorized,
            "total_unauthorized": len(unauthorized),
        }

    except OltError as e:
        return {"connected": False, "error": str(e), "host": data.host}


# ================================================================
# CONEXIÓN POR CÉLULA — endpoints existentes
# ================================================================

@router.get("/test/{cell_id}")
async def test_olt_connection(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Prueba la conexión SSH a la OLT de una célula."""
    try:
        driver = await get_olt_for_cell(db, cell_id, user.tenant_id)
        result = await driver.test_connection()
        return result
    except OltError as e:
        return {"connected": False, "error": str(e)}


@router.get("/unauthorized-onus/{cell_id}")
async def list_unauthorized_onus(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista ONUs detectadas pero no autorizadas (parpadeando)."""
    try:
        driver = await get_olt_for_cell(db, cell_id, user.tenant_id)
        onus = await driver.list_unauthorized_onus()
        return {
            "cell_id": cell_id,
            "total": len(onus),
            "unauthorized_onus": [
                {
                    "serial_number": onu.serial_number,
                    "slot": onu.slot,
                    "pon_port": onu.pon_port,
                    "model": onu.model,
                    "status": onu.status,
                }
                for onu in onus
            ]
        }
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")


@router.post("/authorize-onu")
async def authorize_onu_in_olt(
    data: AuthorizeOnuOltRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Autoriza una ONU directamente en la OLT."""
    try:
        driver = await get_olt_for_cell(db, data.cell_id, user.tenant_id)
        result = await driver.authorize_onu(
            serial_number=data.serial_number,
            slot=data.slot,
            pon_port=data.pon_port,
            onu_id=data.onu_id,
            onu_type=data.onu_type,
            line_profile=data.line_profile,
            remote_profile=data.remote_profile,
            vlan=data.vlan,
            description=data.description,
        )
        return {"message": "ONU autorizada", "result": result}
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")


@router.post("/deauthorize-onu")
async def deauthorize_onu_from_olt(
    data: DeauthorizeOnuOltRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Elimina una ONU de la OLT. La ONU vuelve a parpadear."""
    try:
        driver = await get_olt_for_cell(db, data.cell_id, user.tenant_id)
        result = await driver.deauthorize_onu(
            slot=data.slot,
            pon_port=data.pon_port,
            onu_id=data.onu_id,
        )
        return {"message": "ONU desautorizada", "result": result}
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")


@router.get("/onu-status/{cell_id}")
async def get_onu_status(
    cell_id: int,
    slot: int = Query(...),
    pon_port: int = Query(...),
    onu_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Obtiene el estado de una ONU específica (online/offline)."""
    try:
        driver = await get_olt_for_cell(db, cell_id, user.tenant_id)
        onu = await driver.get_onu_status(slot=slot, pon_port=pon_port, onu_id=onu_id)
        return {
            "cell_id": cell_id,
            "onu_id": onu.onu_id,
            "serial_number": onu.serial_number,
            "status": onu.status,
            "slot": onu.slot,
            "pon_port": onu.pon_port,
            "rx_power": onu.rx_power,
        }
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")


@router.get("/onu-optical/{cell_id}")
async def get_onu_optical_info(
    cell_id: int,
    slot: int = Query(...),
    pon_port: int = Query(...),
    onu_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Obtiene información óptica de una ONU.
    Rx Power, Tx Power, temperatura, voltaje.
    Nivel normal: -8 a -23 dBm. Alerta si menor a -25 dBm.
    """
    try:
        driver = await get_olt_for_cell(db, cell_id, user.tenant_id)
        info = await driver.get_onu_optical_info(slot=slot, pon_port=pon_port, onu_id=onu_id)

        rx = info.get("rx_power")
        if rx is not None:
            if rx >= -8:     info["signal_quality"] = "excelente"
            elif rx >= -15:  info["signal_quality"] = "buena"
            elif rx >= -23:  info["signal_quality"] = "aceptable"
            elif rx >= -25:  info["signal_quality"] = "baja"
            else:            info["signal_quality"] = "critica"

        return {"cell_id": cell_id, "onu_id": onu_id, **info}
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")


@router.get("/onus-on-port/{cell_id}")
async def list_onus_on_pon_port(
    cell_id: int,
    slot: int = Query(...),
    pon_port: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista todas las ONUs registradas en un puerto PON."""
    try:
        driver = await get_olt_for_cell(db, cell_id, user.tenant_id)
        onus = await driver.list_onus_on_port(slot=slot, pon_port=pon_port)
        return {
            "cell_id": cell_id,
            "slot": slot,
            "pon_port": pon_port,
            "total": len(onus),
            "onus": [
                {
                    "onu_id": onu.onu_id,
                    "serial_number": onu.serial_number,
                    "status": onu.status,
                    "model": onu.model,
                    "rx_power": onu.rx_power,
                }
                for onu in onus
            ]
        }
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")


@router.post("/configure-service")
async def configure_onu_service(
    data: ConfigureServiceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Configura VLAN de servicio en una ONU ya autorizada."""
    try:
        driver = await get_olt_for_cell(db, data.cell_id, user.tenant_id)
        result = await driver.configure_onu_service(
            slot=data.slot,
            pon_port=data.pon_port,
            onu_id=data.onu_id,
            vlan=data.vlan,
            service_port=data.service_port,
        )
        return {"message": "Servicio configurado", "result": result}
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")


@router.post("/execute-command")
async def execute_raw_command(
    data: ExecuteCommandRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Ejecuta un comando SSH raw en la OLT. Solo para técnicos avanzados."""
    try:
        driver = await get_olt_for_cell(db, data.cell_id, user.tenant_id)
        output = await driver.execute_command(command=data.command, timeout=data.timeout)
        return {
            "cell_id": data.cell_id,
            "command": data.command,
            "output": output,
        }
    except OltError as e:
        raise HTTPException(502, f"Error OLT: {e}")