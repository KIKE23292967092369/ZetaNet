"""
Sistema ISP - Driver OLT VSOL
Implementa comandos SSH/Telnet específicos para OLTs VSOL.

Las OLTs VSOL usan un CLI similar al estilo Cisco/Linux.
Comandos principales varían por modelo pero siguen un patrón común.
"""
import asyncio
import re
import logging
from typing import Optional, List, Dict, Any

from app.services.olt.olt_base import OltDriverBase, OltCredentials, OnuInfo, OltError

logger = logging.getLogger("olt_vsol")

CMD_TIMEOUT = 30


class VsolDriver(OltDriverBase):
    """
    Driver para OLTs VSOL.
    Conecta por SSH y ejecuta comandos del CLI VSOL.
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
        """Conecta por SSH a la OLT VSOL."""
        try:
            import asyncssh

            self._connection = await asyncio.wait_for(
                asyncssh.connect(
                    host=self.credentials.host,
                    port=self.credentials.ssh_port,
                    username=self.credentials.ssh_username,
                    password=self.credentials.ssh_password,
                    known_hosts=None,
                    connect_timeout=15
                ),
                timeout=20
            )

            self._stdin, self._stdout, self._stderr = await self._connection.open_session(
                term_type="vt100"
            )

            await self._read_until_prompt(timeout=10)
            logger.info(f"Conectado a OLT VSOL {self.credentials.host}")
            return True

        except ImportError:
            raise OltError("Librería asyncssh no instalada. Ejecutar: pip install asyncssh")
        except asyncio.TimeoutError:
            raise OltError(f"Timeout conectando a OLT VSOL {self.credentials.host}")
        except Exception as e:
            raise OltError(f"Error conectando a OLT VSOL {self.credentials.host}: {e}")

    async def disconnect(self):
        """Cierra la conexión SSH."""
        try:
            if self._connection:
                self._connection.close()
                self._connection = None
                logger.info(f"Desconectado de OLT VSOL {self.credentials.host}")
        except Exception:
            pass

    async def test_connection(self) -> Dict[str, Any]:
        """Prueba conexión y obtiene info del equipo."""
        try:
            await self.connect()

            version_output = await self._send_command("show version")

            await self.disconnect()

            return {
                "connected": True,
                "brand": "VSOL",
                "model": self.credentials.model or "VSOL-OLT",
                "host": self.credentials.host,
                "version_info": version_output[:500]
            }

        except OltError as e:
            return {
                "connected": False,
                "brand": "VSOL",
                "host": self.credentials.host,
                "error": str(e)
            }

    # ================================================================
    # ONUs NO AUTORIZADAS
    # ================================================================

    async def list_unauthorized_onus(self) -> List[OnuInfo]:
        """
        Lista ONUs no autorizadas.
        Comando VSOL: show pon onu uncfg
        """
        try:
            await self.connect()
            output = await self._send_command("show pon onu uncfg")
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
        Autoriza una ONU en la OLT VSOL.
        
        Secuencia de comandos VSOL:
        1. configure terminal
        2. interface epon/gpon 0/{slot}
        3. onu {onu_id} sn {serial} (o bind)
        4. exit
        5. Configurar VLAN si aplica
        """
        try:
            await self.connect()

            await self._send_command("configure terminal")

            # Seleccionar interfaz PON
            iface = f"gpon 0/{slot}/{pon_port}"
            await self._send_command(f"interface {iface}")

            # Autorizar ONU
            if onu_id:
                cmd = f"onu {onu_id} sn {serial_number}"
            else:
                cmd = f"onu bind sn {serial_number}"

            if onu_type:
                cmd += f" type {onu_type}"

            auth_output = await self._send_command(cmd)

            await self._send_command("exit")

            # Configurar VLAN si se proporciona
            if vlan and onu_id:
                await self._configure_vlan(slot, pon_port, onu_id, vlan)

            await self._send_command("exit")

            await self.disconnect()

            assigned_id = onu_id or self._parse_assigned_onu_id(auth_output)

            logger.info(
                f"ONU autorizada en VSOL: SN={serial_number}, "
                f"Slot={slot}, PON={pon_port}, ID={assigned_id}"
            )

            return {
                "status": "authorized",
                "serial_number": serial_number,
                "slot": slot,
                "pon_port": pon_port,
                "onu_id": assigned_id,
                "vlan": vlan,
                "raw_output": auth_output[:300]
            }

        except OltError:
            await self.disconnect()
            raise
        except Exception as e:
            await self.disconnect()
            raise OltError(f"Error autorizando ONU en VSOL: {e}")

    async def deauthorize_onu(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> Dict[str, Any]:
        """
        Elimina una ONU de la OLT VSOL.
        """
        try:
            await self.connect()

            await self._send_command("configure terminal")
            iface = f"gpon 0/{slot}/{pon_port}"
            await self._send_command(f"interface {iface}")
            output = await self._send_command(f"no onu {onu_id}")
            await self._send_command("exit")
            await self._send_command("exit")

            await self.disconnect()

            logger.info(f"ONU eliminada de VSOL: Slot={slot}, PON={pon_port}, ID={onu_id}")

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
            raise OltError(f"Error eliminando ONU de VSOL: {e}")

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
        Obtiene estado de una ONU VSOL.
        Comando: show pon onu information gpon 0/{slot}/{pon_port} {onu_id}
        """
        try:
            await self.connect()

            cmd = f"show pon onu information gpon 0/{slot}/{pon_port} {onu_id}"
            output = await self._send_command(cmd)

            await self.disconnect()

            return self._parse_onu_info(output, onu_id, slot, pon_port)

        except OltError:
            raise
        except Exception as e:
            raise OltError(f"Error obteniendo estado ONU VSOL: {e}")

    async def get_onu_optical_info(
        self,
        slot: int,
        pon_port: int,
        onu_id: int
    ) -> Dict[str, Any]:
        """
        Obtiene información óptica de una ONU VSOL.
        Comando: show pon onu optical-info gpon 0/{slot}/{pon_port} {onu_id}
        """
        try:
            await self.connect()

            cmd = f"show pon onu optical-info gpon 0/{slot}/{pon_port} {onu_id}"
            output = await self._send_command(cmd)

            await self.disconnect()

            return self._parse_optical_info(output)

        except OltError:
            raise
        except Exception as e:
            raise OltError(f"Error obteniendo info óptica VSOL: {e}")

    async def list_onus_on_port(
        self,
        slot: int,
        pon_port: int
    ) -> List[OnuInfo]:
        """
        Lista ONUs registradas en un puerto PON VSOL.
        Comando: show pon onu information gpon 0/{slot}/{pon_port}
        """
        try:
            await self.connect()

            cmd = f"show pon onu information gpon 0/{slot}/{pon_port}"
            output = await self._send_command(cmd)

            await self.disconnect()

            return self._parse_all_onus(output, slot, pon_port)

        except OltError:
            raise
        except Exception as e:
            raise OltError(f"Error listando ONUs en puerto VSOL: {e}")

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
        """Configura VLAN de servicio en ONU VSOL."""
        try:
            await self.connect()

            await self._send_command("configure terminal")
            output = await self._configure_vlan(slot, pon_port, onu_id, vlan)
            await self._send_command("exit")

            await self.disconnect()

            return {
                "status": "configured",
                "slot": slot,
                "pon_port": pon_port,
                "onu_id": onu_id,
                "vlan": vlan,
                "raw_output": output[:300] if output else ""
            }

        except OltError:
            await self.disconnect()
            raise
        except Exception as e:
            await self.disconnect()
            raise OltError(f"Error configurando servicio VSOL: {e}")

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
            raise OltError(f"Error ejecutando comando VSOL: {e}")

    # ================================================================
    # HELPERS INTERNOS
    # ================================================================

    async def _send_command(self, command: str, timeout: int = CMD_TIMEOUT) -> str:
        """Envía un comando y espera la respuesta."""
        if not self._stdin or not self._stdout:
            raise OltError("No hay conexión SSH activa")

        self._stdin.write(command + "\n")
        output = await self._read_until_prompt(timeout=timeout)
        return output

    async def _read_until_prompt(self, timeout: int = 15) -> str:
        """Lee la salida hasta encontrar un prompt."""
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

                if re.search(r'[#>]\s*$', output):
                    break

        except asyncio.TimeoutError:
            pass

        return output

    async def _configure_vlan(self, slot: int, pon_port: int, onu_id: int, vlan: str) -> str:
        """Configura VLAN en una ONU VSOL."""
        iface = f"gpon 0/{slot}/{pon_port}"
        await self._send_command(f"interface {iface}")
        output = await self._send_command(
            f"onu {onu_id} vlan {vlan} translate {vlan}"
        )
        await self._send_command("exit")
        return output

    # ================================================================
    # PARSERS
    # ================================================================

    def _parse_uncfg_onus(self, output: str) -> List[OnuInfo]:
        """Parsea ONUs no autorizadas de VSOL."""
        onus = []
        for line in output.split("\n"):
            line = line.strip()

            # Buscar patrón: slot/port  serial  type
            match = re.search(
                r'(\d+)/(\d+)\s+(\S{8,})\s+(\S+)',
                line
            )
            if match:
                slot = int(match.group(1))
                port = int(match.group(2))
                serial = match.group(3)
                onu_type = match.group(4)

                onus.append(OnuInfo(
                    serial_number=serial,
                    slot=slot,
                    pon_port=port,
                    status="unauthorized",
                    model=onu_type
                ))

        return onus

    def _parse_assigned_onu_id(self, output: str) -> Optional[int]:
        """Parsea ID asignado."""
        match = re.search(r'onu\s+(\d+)', output, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _parse_onu_info(self, output: str, onu_id: int, slot: int, pon_port: int) -> OnuInfo:
        """Parsea información de una ONU VSOL."""
        status = "unknown"
        serial = ""
        rx_power = None

        if "online" in output.lower():
            status = "online"
        elif "offline" in output.lower():
            status = "offline"

        sn_match = re.search(r'[Ss]erial[:\s]+(\S+)', output)
        if sn_match:
            serial = sn_match.group(1)

        rx_match = re.search(r'[Rr]x\s*[Pp]ower[:\s]+(-?\d+\.?\d*)', output)
        if rx_match:
            rx_power = float(rx_match.group(1))

        return OnuInfo(
            serial_number=serial,
            onu_id=onu_id,
            slot=slot,
            pon_port=pon_port,
            status=status,
            rx_power=rx_power
        )

    def _parse_all_onus(self, output: str, slot: int, pon_port: int) -> List[OnuInfo]:
        """Parsea lista de ONUs en un puerto VSOL."""
        onus = []
        for line in output.split("\n"):
            match = re.search(
                r'(\d+)\s+(\S{8,})\s+(\S+)',
                line
            )
            if match:
                onu_id = int(match.group(1))
                serial = match.group(2)
                status_raw = match.group(3).lower()
                status = "online" if "online" in status_raw or "active" in status_raw else "offline"

                onus.append(OnuInfo(
                    serial_number=serial,
                    onu_id=onu_id,
                    slot=slot,
                    pon_port=pon_port,
                    status=status
                ))

        return onus

    def _parse_optical_info(self, output: str) -> Dict[str, Any]:
        """Parsea información óptica VSOL."""
        info = {
            "rx_power": None,
            "tx_power": None,
            "temperature": None,
            "voltage": None,
            "raw_output": output[:500]
        }

        rx_match = re.search(r'[Rr]x\s*(?:[Oo]ptical\s*)?[Pp]ower[:\s]+(-?\d+\.?\d*)', output)
        if rx_match:
            info["rx_power"] = float(rx_match.group(1))

        tx_match = re.search(r'[Tt]x\s*(?:[Oo]ptical\s*)?[Pp]ower[:\s]+(-?\d+\.?\d*)', output)
        if tx_match:
            info["tx_power"] = float(tx_match.group(1))

        temp_match = re.search(r'[Tt]emperature[:\s]+(-?\d+\.?\d*)', output)
        if temp_match:
            info["temperature"] = float(temp_match.group(1))

        return info