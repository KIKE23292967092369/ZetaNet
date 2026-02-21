"""
Sistema ISP - Driver OLT ZTE (ZXA10 C300, C320, C600)
Implementa comandos SSH específicos para OLTs ZTE.

Comandos principales:
  - show gpon onu uncfg → ONUs no autorizadas
  - show gpon onu state gpon-olt_X/X → Estado ONUs
  - show gpon onu optical-info gpon-onu_X/X:X → Señal óptica
  - conf t → modo configuración
  - interface gpon-olt_X/X → seleccionar puerto PON
  - onu X type Y sn Z → autorizar ONU
"""
import asyncio
import re
import logging
from typing import Optional, List, Dict, Any

from app.services.olt.olt_base import OltDriverBase, OltCredentials, OnuInfo, OltError

logger = logging.getLogger("olt_zte")

# Timeout para comandos SSH
CMD_TIMEOUT = 30


class ZteDriver(OltDriverBase):
    """
    Driver para OLTs ZTE (ZXA10 C300, C320, C600).
    Conecta por SSH y ejecuta comandos del CLI ZTE.
    """

    def __init__(self, credentials: OltCredentials):
        super().__init__(credentials)
        self._connection = None
        self._stdin = None
        self._stdout = None
        self._stderr = None

    # ================================================================
    # CONEXIÓN SSH
    # ================================================================

    async def connect(self) -> bool:
        """Conecta por SSH a la OLT ZTE."""
        try:
            import asyncssh

            self._connection = await asyncio.wait_for(
                asyncssh.connect(
                    host=self.credentials.host,
                    port=self.credentials.ssh_port,
                    username=self.credentials.ssh_username,
                    password=self.credentials.ssh_password,
                    known_hosts=None,  # No verificar host key en producción usar known_hosts
                    connect_timeout=15
                ),
                timeout=20
            )

            # Abrir sesión interactiva
            self._stdin, self._stdout, self._stderr = await self._connection.open_session(
                term_type="vt100"
            )

            # Esperar prompt inicial
            await self._read_until_prompt(timeout=10)
            logger.info(f"Conectado a OLT ZTE {self.credentials.host}")
            return True

        except ImportError:
            raise OltError("Librería asyncssh no instalada. Ejecutar: pip install asyncssh")
        except asyncio.TimeoutError:
            raise OltError(f"Timeout conectando a OLT ZTE {self.credentials.host}")
        except Exception as e:
            raise OltError(f"Error conectando a OLT ZTE {self.credentials.host}: {e}")

    async def disconnect(self):
        """Cierra la conexión SSH."""
        try:
            if self._connection:
                self._connection.close()
                self._connection = None
                logger.info(f"Desconectado de OLT ZTE {self.credentials.host}")
        except Exception:
            pass

    async def test_connection(self) -> Dict[str, Any]:
        """Prueba conexión y obtiene info del equipo."""
        try:
            await self.connect()

            # Obtener versión
            version_output = await self._send_command("show version")
            hostname_output = await self._send_command("show hostname")

            await self.disconnect()

            return {
                "connected": True,
                "brand": "ZTE",
                "model": self.credentials.model or "ZXA10",
                "host": self.credentials.host,
                "hostname": self._parse_hostname(hostname_output),
                "version_info": version_output[:500]  # Primeros 500 chars
            }

        except OltError as e:
            return {
                "connected": False,
                "brand": "ZTE",
                "host": self.credentials.host,
                "error": str(e)
            }

    # ================================================================
    # ONUs NO AUTORIZADAS
    # ================================================================

    async def list_unauthorized_onus(self) -> List[OnuInfo]:
        """
        Lista ONUs no autorizadas (parpadeando).
        Comando: show gpon onu uncfg
        """
        try:
            await self.connect()
            output = await self._send_command("show gpon onu uncfg")
            await self.disconnect()

            return self._parse_uncfg_onus(output)

        except OltError:
            raise
        except Exception as e:
            raise OltError(f"Error listando ONUs no autorizadas: {e}")

    # ================================================================
    # AUTORIZAR ONU
    # ================================================================

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
        Autoriza una ONU en la OLT ZTE.
        
        Secuencia de comandos:
        1. conf t
        2. interface gpon-olt_1/{slot}/{pon_port}
        3. onu {onu_id} type {onu_type} sn {serial}
        4. exit
        5. (Opcional) Configurar servicio/VLAN
        """
        try:
            await self.connect()

            # Entrar a modo configuración
            await self._send_command("configure terminal")

            # Seleccionar interfaz GPON
            iface = f"gpon-olt_1/{slot}/{pon_port}"
            await self._send_command(f"interface {iface}")

            # Construir comando de autorización
            if onu_id:
                cmd = f"onu {onu_id} type {onu_type} sn {serial_number}"
            else:
                cmd = f"onu auto type {onu_type} sn {serial_number}"

            if description:
                cmd += f" desc \"{description}\""

            auth_output = await self._send_command(cmd)

            # Salir de la interfaz
            await self._send_command("exit")

            # Configurar line-profile y remote-profile si se proporcionan
            if line_profile or remote_profile or vlan:
                onu_ref = f"gpon-onu_1/{slot}/{pon_port}:{onu_id}" if onu_id else ""
                if onu_ref:
                    await self._configure_onu_profiles(
                        onu_ref, line_profile, remote_profile, vlan
                    )

            # Salir de modo configuración
            await self._send_command("exit")

            await self.disconnect()

            # Parsear resultado
            assigned_id = onu_id or self._parse_assigned_onu_id(auth_output)

            logger.info(
                f"ONU autorizada en ZTE: SN={serial_number}, "
                f"Slot={slot}, PON={pon_port}, ID={assigned_id}"
            )

            return {
                "status": "authorized",
                "serial_number": serial_number,
                "slot": slot,
                "pon_port": pon_port,
                "onu_id": assigned_id,
                "onu_type": onu_type,
                "line_profile": line_profile,
                "remote_profile": remote_profile,
                "vlan": vlan,
                "raw_output": auth_output[:300]
            }

        except OltError:
            await self.disconnect()
            raise
        except Exception as e:
            await self.disconnect()
            raise OltError(f"Error autorizando ONU en ZTE: {e}")

    async def deauthorize_onu(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> Dict[str, Any]:
        """
        Elimina una ONU de la OLT ZTE.
        
        Comandos:
        1. conf t
        2. interface gpon-olt_1/{slot}/{pon_port}
        3. no onu {onu_id}
        4. exit / exit
        """
        try:
            await self.connect()

            await self._send_command("configure terminal")
            iface = f"gpon-olt_1/{slot}/{pon_port}"
            await self._send_command(f"interface {iface}")
            output = await self._send_command(f"no onu {onu_id}")
            await self._send_command("exit")
            await self._send_command("exit")

            await self.disconnect()

            logger.info(f"ONU eliminada de ZTE: Slot={slot}, PON={pon_port}, ID={onu_id}")

            return {
                "status": "deauthorized",
                "slot": slot,
                "pon_port": pon_port,
                "onu_id": onu_id,
                "raw_output": output[:300]
            }

        except OltError:
            await self.disconnect()
            raise
        except Exception as e:
            await self.disconnect()
            raise OltError(f"Error eliminando ONU de ZTE: {e}")

    # ================================================================
    # ESTADO Y SEÑAL
    # ================================================================

    async def get_onu_status(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> OnuInfo:
        """
        Obtiene estado de una ONU.
        Comando: show gpon onu state gpon-olt_1/{slot}/{pon_port}
        """
        try:
            await self.connect()

            cmd = f"show gpon onu state gpon-olt_1/{slot}/{pon_port}"
            output = await self._send_command(cmd)

            await self.disconnect()

            return self._parse_onu_state(output, onu_id)

        except OltError:
            raise
        except Exception as e:
            raise OltError(f"Error obteniendo estado ONU: {e}")

    async def get_onu_optical_info(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> Dict[str, Any]:
        """
        Obtiene información óptica de una ONU.
        Comando: show gpon onu optical-info gpon-onu_1/{slot}/{pon_port}:{onu_id}
        """
        try:
            await self.connect()

            onu_ref = f"gpon-onu_1/{slot}/{pon_port}:{onu_id}"
            cmd = f"show gpon onu optical-info {onu_ref}"
            output = await self._send_command(cmd)

            await self.disconnect()

            return self._parse_optical_info(output)

        except OltError:
            raise
        except Exception as e:
            raise OltError(f"Error obteniendo info óptica: {e}")

    async def list_onus_on_port(
        self,
        slot: int,
        pon_port: int
    ) -> List[OnuInfo]:
        """
        Lista ONUs registradas en un puerto PON.
        Comando: show gpon onu state gpon-olt_1/{slot}/{pon_port}
        """
        try:
            await self.connect()

            cmd = f"show gpon onu state gpon-olt_1/{slot}/{pon_port}"
            output = await self._send_command(cmd)

            await self.disconnect()

            return self._parse_all_onu_states(output, slot, pon_port)

        except OltError:
            raise
        except Exception as e:
            raise OltError(f"Error listando ONUs en puerto: {e}")

    # ================================================================
    # CONFIGURACIÓN DE SERVICIO
    # ================================================================

    async def configure_onu_service(
        self,
        slot: int,
        pon_port: int,
        onu_id: int,
        vlan: str,
        service_port: int = 1
    ) -> Dict[str, Any]:
        """
        Configura servicio VLAN en ONU ZTE.
        
        Comandos:
        1. conf t
        2. pon-onu-mng gpon-onu_1/{slot}/{pon_port}:{onu_id}
        3. service-port {sp} vport {sp} user-vlan {vlan} vlan {vlan}
        4. exit / exit
        """
        try:
            await self.connect()

            onu_ref = f"gpon-onu_1/{slot}/{pon_port}:{onu_id}"

            await self._send_command("configure terminal")
            await self._send_command(f"pon-onu-mng {onu_ref}")
            output = await self._send_command(
                f"service-port {service_port} vport {service_port} "
                f"user-vlan {vlan} vlan {vlan}"
            )
            await self._send_command("exit")
            await self._send_command("exit")

            await self.disconnect()

            logger.info(f"Servicio configurado en ONU {onu_ref}: VLAN {vlan}")

            return {
                "status": "configured",
                "onu_ref": onu_ref,
                "vlan": vlan,
                "service_port": service_port,
                "raw_output": output[:300]
            }

        except OltError:
            await self.disconnect()
            raise
        except Exception as e:
            await self.disconnect()
            raise OltError(f"Error configurando servicio en ONU: {e}")

    # ================================================================
    # COMANDO RAW
    # ================================================================

    async def execute_command(self, command: str, timeout: int = 30) -> str:
        """Ejecuta un comando SSH raw."""
        try:
            await self.connect()
            output = await self._send_command(command, timeout=timeout)
            await self.disconnect()
            return output
        except Exception as e:
            await self.disconnect()
            raise OltError(f"Error ejecutando comando: {e}")

    # ================================================================
    # HELPERS INTERNOS - SSH
    # ================================================================

    async def _send_command(self, command: str, timeout: int = CMD_TIMEOUT) -> str:
        """Envía un comando y espera la respuesta."""
        if not self._stdin or not self._stdout:
            raise OltError("No hay conexión SSH activa")

        self._stdin.write(command + "\n")

        output = await self._read_until_prompt(timeout=timeout)
        return output

    async def _read_until_prompt(self, timeout: int = 15) -> str:
        """Lee la salida SSH hasta encontrar un prompt."""
        output = ""
        try:
            while True:
                chunk = await asyncio.wait_for(
                    self._stdout.read(4096),
                    timeout=timeout
                )
                if not chunk:
                    break
                output += chunk

                # Detectar prompts ZTE: hostname#, hostname(config)#, hostname(config-if)#
                if re.search(r'[#>]\s*$', output):
                    break

        except asyncio.TimeoutError:
            pass  # Retornar lo que se haya leído

        return output

    # ================================================================
    # HELPERS INTERNOS - CONFIGURACIÓN
    # ================================================================

    async def _configure_onu_profiles(
        self,
        onu_ref: str,
        line_profile: str,
        remote_profile: str,
        vlan: str
    ):
        """Configura perfiles y VLAN en una ONU recién autorizada."""
        if line_profile:
            await self._send_command(
                f"pon-onu-mng {onu_ref}"
            )
            if line_profile:
                await self._send_command(f"tcont 1 profile {line_profile}")
            if remote_profile:
                await self._send_command(f"gemport 1 tcont 1")
            if vlan:
                await self._send_command(
                    f"service-port 1 vport 1 user-vlan {vlan} vlan {vlan}"
                )
            await self._send_command("exit")

    # ================================================================
    # PARSERS - Interpretan la salida del CLI ZTE
    # ================================================================

    def _parse_hostname(self, output: str) -> str:
        """Extrae hostname de la salida."""
        for line in output.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "hostname" not in line.lower():
                return line
        return "ZTE-OLT"

    def _parse_uncfg_onus(self, output: str) -> List[OnuInfo]:
        """
        Parsea salida de 'show gpon onu uncfg'.
        Formato típico ZTE:
        ONU  SN              Type        ...
        gpon-olt_1/4/1  ZTEG12345678  ZTE-F670L  ...
        """
        onus = []
        for line in output.split("\n"):
            line = line.strip()

            # Buscar líneas con gpon-olt_
            match = re.search(
                r'gpon-olt_(\d+)/(\d+)/(\d+)\s+(\S+)\s+(\S+)',
                line
            )
            if match:
                frame, slot, port = int(match.group(1)), int(match.group(2)), int(match.group(3))
                serial = match.group(4)
                onu_type = match.group(5)

                onus.append(OnuInfo(
                    serial_number=serial,
                    slot=slot,
                    pon_port=port,
                    status="unauthorized",
                    model=onu_type
                ))

        return onus

    def _parse_assigned_onu_id(self, output: str) -> Optional[int]:
        """Parsea el ID asignado a una ONU recién autorizada."""
        match = re.search(r'onu\s+(\d+)\s+type', output, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.search(r'ONU\s*ID\s*[=:]\s*(\d+)', output, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    def _parse_onu_state(self, output: str, onu_id: int) -> OnuInfo:
        """Parsea estado de una ONU específica de 'show gpon onu state'."""
        for line in output.split("\n"):
            # Buscar línea con el onu_id
            match = re.search(
                r'gpon-onu_\d+/(\d+)/(\d+):(\d+)\s+(\S+)\s+(\S+)',
                line
            )
            if match and int(match.group(3)) == onu_id:
                return OnuInfo(
                    serial_number="",
                    onu_id=onu_id,
                    slot=int(match.group(1)),
                    pon_port=int(match.group(2)),
                    status="online" if "working" in match.group(5).lower() else "offline"
                )

        return OnuInfo(serial_number="", onu_id=onu_id, status="unknown")

    def _parse_all_onu_states(self, output: str, slot: int, pon_port: int) -> List[OnuInfo]:
        """Parsea todos los estados de ONUs en un puerto."""
        onus = []
        for line in output.split("\n"):
            match = re.search(
                r'gpon-onu_\d+/\d+/\d+:(\d+)\s+(\S+)\s+(\S+)',
                line
            )
            if match:
                onu_id = int(match.group(1))
                status_raw = match.group(3).lower()
                status = "online" if "working" in status_raw else "offline"

                onus.append(OnuInfo(
                    serial_number=match.group(2) if len(match.group(2)) > 5 else "",
                    onu_id=onu_id,
                    slot=slot,
                    pon_port=pon_port,
                    status=status
                ))

        return onus

    def _parse_optical_info(self, output: str) -> Dict[str, Any]:
        """
        Parsea información óptica de 'show gpon onu optical-info'.
        Busca Rx Power, Tx Power, Temperature, Voltage, Bias Current.
        """
        info = {
            "rx_power": None,
            "tx_power": None,
            "temperature": None,
            "voltage": None,
            "bias_current": None,
            "raw_output": output[:500]
        }

        # Rx optical power (dBm)
        match = re.search(r'Rx\s*(?:optical\s*)?power[:\s]+(-?\d+\.?\d*)\s*(?:dBm)?', output, re.IGNORECASE)
        if match:
            info["rx_power"] = float(match.group(1))

        # Tx optical power (dBm)
        match = re.search(r'Tx\s*(?:optical\s*)?power[:\s]+(-?\d+\.?\d*)\s*(?:dBm)?', output, re.IGNORECASE)
        if match:
            info["tx_power"] = float(match.group(1))

        # Temperature
        match = re.search(r'[Tt]emperature[:\s]+(-?\d+\.?\d*)', output)
        if match:
            info["temperature"] = float(match.group(1))

        # Voltage
        match = re.search(r'[Vv]oltage[:\s]+(\d+\.?\d*)', output)
        if match:
            info["voltage"] = float(match.group(1))

        return info