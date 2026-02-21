"""
Sistema ISP - OLT Base (Clase Abstracta)
Define la interfaz que todos los drivers de OLT deben implementar.
Cada marca (ZTE, VSOL, Huawei, FiberHome) implementa estos métodos
con sus comandos específicos.

Comunicación: SSH (puerto 22) para comandos, SNMP (puerto 161) para monitoreo.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger("olt_base")


@dataclass
class OltCredentials:
    """Credenciales de conexión a una OLT."""
    host: str
    ssh_port: int = 22
    ssh_username: str = "admin"
    ssh_password: str = ""
    snmp_port: int = 161
    snmp_community: str = "public"
    snmp_version: str = "2c"
    brand: str = ""
    model: str = ""


@dataclass
class OnuInfo:
    """Información de una ONU detectada o registrada."""
    serial_number: str
    onu_id: Optional[int] = None
    slot: Optional[int] = None
    pon_port: Optional[int] = None
    status: str = "unknown"          # online, offline, unauthorized
    rx_power: Optional[float] = None  # dBm recepción en OLT
    tx_power: Optional[float] = None  # dBm transmisión de ONU
    distance: Optional[int] = None    # metros
    model: str = ""
    description: str = ""
    line_profile: str = ""
    remote_profile: str = ""
    vlan: str = ""


class OltError(Exception):
    """Error de comunicación con OLT."""
    pass


class OltDriverBase(ABC):
    """
    Clase base abstracta para drivers de OLT.
    Cada fabricante implementa estos métodos con sus comandos SSH específicos.
    
    Uso:
        driver = ZteDriver(credentials)
        await driver.connect()
        onus = await driver.list_unauthorized_onus()
        await driver.authorize_onu(serial, slot, port, ...)
        await driver.disconnect()
    """

    def __init__(self, credentials: OltCredentials):
        self.credentials = credentials
        self._connection = None

    @property
    def brand(self) -> str:
        return self.credentials.brand

    @property
    def model(self) -> str:
        return self.credentials.model

    # ================================================================
    # CONEXIÓN SSH
    # ================================================================

    @abstractmethod
    async def connect(self) -> bool:
        """Establece conexión SSH con la OLT."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Cierra la conexión SSH."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión y retorna info del equipo.
        Returns: {"connected": bool, "brand": str, "model": str, "version": str, ...}
        """
        pass

    # ================================================================
    # ONUs NO AUTORIZADAS (PENDIENTES)
    # ================================================================

    @abstractmethod
    async def list_unauthorized_onus(self) -> List[OnuInfo]:
        """
        Lista ONUs detectadas pero no autorizadas.
        Estas son las que "parpadean" esperando ser registradas.
        """
        pass

    # ================================================================
    # AUTORIZAR / DESAUTORIZAR ONU
    # ================================================================

    @abstractmethod
    async def authorize_onu(
        self,
        serial_number: str,
        slot: int,
        pon_port: int,
        onu_id: Optional[int] = None,
        onu_type: str = "",
        line_profile: str = "",
        remote_profile: str = "",
        vlan: str = "",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Autoriza/registra una ONU en la OLT.
        La ONU deja de parpadear y se sincroniza.
        
        Args:
            serial_number: Serial de la ONU (ej: "ZTEG1234ABCD")
            slot: Slot de la tarjeta GPON (ej: 1)
            pon_port: Puerto PON (ej: 4)
            onu_id: ID asignado (si None, la OLT asigna automático)
            onu_type: Tipo/familia de ONU (ej: "ZTE-F670L")
            line_profile: Perfil de línea
            remote_profile: Perfil remoto
            vlan: VLAN de servicio (ej: "100")
            description: Descripción/comentario
        
        Returns:
            {"status": "authorized", "onu_id": int, ...}
        """
        pass

    @abstractmethod
    async def deauthorize_onu(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> Dict[str, Any]:
        """
        Desautoriza/elimina una ONU de la OLT.
        La ONU vuelve a parpadear (pierde sincronización).
        """
        pass

    # ================================================================
    # ESTADO Y SEÑAL
    # ================================================================

    @abstractmethod
    async def get_onu_status(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> OnuInfo:
        """
        Obtiene el estado de una ONU específica.
        Incluye: online/offline, señal, distancia.
        """
        pass

    @abstractmethod
    async def get_onu_optical_info(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> Dict[str, Any]:
        """
        Obtiene información óptica detallada de una ONU.
        Rx Power, Tx Power, temperatura, voltaje.
        """
        pass

    @abstractmethod
    async def list_onus_on_port(
        self,
        slot: int,
        pon_port: int
    ) -> List[OnuInfo]:
        """
        Lista todas las ONUs registradas en un puerto PON específico.
        """
        pass

    # ================================================================
    # CONFIGURACIÓN DE SERVICIO
    # ================================================================

    @abstractmethod
    async def configure_onu_service(
        self,
        slot: int,
        pon_port: int,
        onu_id: int,
        vlan: str,
        service_port: int = 1
    ) -> Dict[str, Any]:
        """
        Configura el servicio (VLAN) en una ONU ya autorizada.
        Esto permite que el tráfico de internet fluya.
        """
        pass

    # ================================================================
    # HELPERS
    # ================================================================

    async def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        Ejecuta un comando SSH raw y retorna la salida.
        Útil para comandos específicos no cubiertos por la interfaz.
        """
        raise NotImplementedError("Implementar en driver específico")

    def parse_frame_slot_port(self, fsp: str) -> tuple:
        """
        Parsea formato Frame/Slot/Port (ej: "0/4/1" → (0, 4, 1))
        """
        parts = fsp.strip().split("/")
        if len(parts) == 3:
            return int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            return 0, int(parts[0]), int(parts[1])
        raise OltError(f"Formato Frame/Slot/Port inválido: {fsp}")