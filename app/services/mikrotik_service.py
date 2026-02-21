"""
Sistema ISP - Servicio MikroTik API 8728
Conecta al MikroTik vía API nativa (puerto 8728).
Gestiona PPPoE Secrets, Simple Queues, Address Lists, Firewall.

Usa librouteros para comunicación con RouterOS.
Todas las operaciones son async vía asyncio.to_thread().

Instalación: pip install librouteros --break-system-packages
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import librouteros
from librouteros import connect
from librouteros.exceptions import (
    TrapError,
    ConnectionClosed,
    FatalError
)

logger = logging.getLogger("mikrotik_service")


@dataclass
class MikroTikCredentials:
    """Credenciales de conexión a un MikroTik."""
    host: str
    port: int = 8728
    username: str = "admin"
    password: str = ""


class MikroTikError(Exception):
    """Error de comunicación con MikroTik."""
    pass


class MikroTikService:
    """
    Servicio para interactuar con MikroTik RouterOS vía API 8728.
    
    Uso:
        service = MikroTikService(host="192.168.88.1", username="admin", password="pass")
        await service.test_connection()
        await service.create_pppoe_secret("user1", "pass1", "10.10.10.5", "default")
    """

    def __init__(self, host: str, port: int = 8728, username: str = "admin", password: str = ""):
        self.credentials = MikroTikCredentials(
            host=host,
            port=port,
            username=username,
            password=password
        )
        self._api = None

    # ================================================================
    # CONEXIÓN
    # ================================================================

    def _connect_sync(self) -> librouteros.api.Api:
        """Conexión síncrona al MikroTik (se ejecuta en thread)."""
        try:
            api = connect(
                host=self.credentials.host,
                port=self.credentials.port,
                username=self.credentials.username,
                password=self.credentials.password,
                timeout=10
            )
            return api
        except (ConnectionRefusedError, OSError) as e:
            raise MikroTikError(
                f"No se pudo conectar a MikroTik {self.credentials.host}:{self.credentials.port} - {e}"
            )
        except TrapError as e:
            raise MikroTikError(f"Error de autenticación en MikroTik: {e}")

    async def _get_api(self):
        """Obtiene conexión al API (crea una nueva cada vez para evitar timeouts)."""
        return await asyncio.to_thread(self._connect_sync)

    async def _execute(self, path: str, command: str = "print", **kwargs) -> List[Dict[str, Any]]:
        """
        Ejecuta un comando en el MikroTik.
        
        Args:
            path: Ruta del API, ej: "/ppp/secret"
            command: Comando (print, add, set, remove)
            **kwargs: Parámetros del comando
        
        Returns:
            Lista de diccionarios con resultados
        """
        try:
            api = await self._get_api()
            try:
                resource = api.path(path)

                if command == "print":
                    result = await asyncio.to_thread(
                        lambda: list(resource)
                    )
                    return result

                elif command == "add":
                    result = await asyncio.to_thread(
                        lambda: resource.add(**kwargs)
                    )
                    return [{"id": result}] if result else []

                elif command == "set":
                    item_id = kwargs.pop("id")
                    await asyncio.to_thread(
                        lambda: resource.update(**{"id": item_id, **kwargs})
                    )
                    return [{"status": "updated"}]

                elif command == "remove":
                    item_id = kwargs.get("id")
                    await asyncio.to_thread(
                        lambda: resource.remove(item_id)
                    )
                    return [{"status": "removed"}]

                else:
                    raise MikroTikError(f"Comando no soportado: {command}")

            finally:
                api.close()

        except TrapError as e:
            raise MikroTikError(f"Error MikroTik [{path}]: {e}")
        except ConnectionClosed:
            raise MikroTikError("Conexión cerrada por el MikroTik")
        except FatalError as e:
            raise MikroTikError(f"Error fatal MikroTik: {e}")
        except Exception as e:
            if isinstance(e, MikroTikError):
                raise
            raise MikroTikError(f"Error inesperado: {e}")

    # ================================================================
    # TEST DE CONEXIÓN
    # ================================================================

    async def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión al MikroTik.
        Retorna info del sistema (identity, version, uptime).
        """
        try:
            result = await self._execute("/system/resource")
            if result:
                info = result[0]
                return {
                    "connected": True,
                    "host": self.credentials.host,
                    "version": info.get("version", "unknown"),
                    "board_name": info.get("board-name", "unknown"),
                    "uptime": info.get("uptime", "unknown"),
                    "cpu_load": info.get("cpu-load", "0"),
                    "free_memory": info.get("free-memory", "0"),
                    "total_memory": info.get("total-memory", "0"),
                }
            return {"connected": True, "host": self.credentials.host}
        except MikroTikError as e:
            return {
                "connected": False,
                "host": self.credentials.host,
                "error": str(e)
            }

    async def get_identity(self) -> str:
        """Obtiene el nombre/identidad del MikroTik."""
        result = await self._execute("/system/identity")
        if result:
            return result[0].get("name", "MikroTik")
        return "MikroTik"

    # ================================================================
    # PPPoE SECRETS (FIBRA)
    # ================================================================

    async def create_pppoe_secret(
        self,
        name: str,
        password: str,
        remote_address: str,
        profile: str = "default",
        local_address: str = "",
        comment: str = "",
        disabled: bool = False
    ) -> Dict[str, Any]:
        """
        Crea un PPPoE Secret en el MikroTik.
        Equivale a: /ppp secret add name=X password=Y remote-address=Z profile=P

        Args:
            name: Usuario PPPoE (ej: jcarlos_fibra)
            password: Contraseña PPPoE
            remote_address: IP que se le asigna al cliente (ej: 10.10.10.100)
            profile: Perfil PPPoE (controla velocidad)
            local_address: IP local del server PPPoE (opcional)
            comment: Comentario identificador
            disabled: Si se crea deshabilitado
        """
        params = {
            "name": name,
            "password": password,
            "service": "pppoe",
            "remote-address": remote_address,
            "profile": profile,
            "comment": comment,
            "disabled": "yes" if disabled else "no"
        }
        if local_address:
            params["local-address"] = local_address

        logger.info(f"Creando PPPoE Secret: {name} → {remote_address} (perfil: {profile})")
        result = await self._execute("/ppp/secret", "add", **params)
        return {"action": "pppoe_secret_created", "name": name, "ip": remote_address, "result": result}

    async def delete_pppoe_secret(self, name: str) -> Dict[str, Any]:
        """
        Elimina un PPPoE Secret por nombre de usuario.
        Primero busca el ID interno del secret, luego lo elimina.
        """
        secrets = await self._execute("/ppp/secret")
        target = None
        for s in secrets:
            if s.get("name") == name:
                target = s
                break

        if not target:
            logger.warning(f"PPPoE Secret no encontrado: {name}")
            return {"action": "pppoe_secret_not_found", "name": name}

        secret_id = target.get(".id")
        await self._execute("/ppp/secret", "remove", id=secret_id)
        logger.info(f"PPPoE Secret eliminado: {name}")
        return {"action": "pppoe_secret_deleted", "name": name}

    async def disable_pppoe_secret(self, name: str) -> Dict[str, Any]:
        """Deshabilita un PPPoE Secret (suspender cliente)."""
        secrets = await self._execute("/ppp/secret")
        for s in secrets:
            if s.get("name") == name:
                await self._execute("/ppp/secret", "set", id=s[".id"], disabled="yes")
                logger.info(f"PPPoE Secret deshabilitado: {name}")
                return {"action": "pppoe_secret_disabled", "name": name}

        return {"action": "pppoe_secret_not_found", "name": name}

    async def enable_pppoe_secret(self, name: str) -> Dict[str, Any]:
        """Habilita un PPPoE Secret (reactivar cliente)."""
        secrets = await self._execute("/ppp/secret")
        for s in secrets:
            if s.get("name") == name:
                await self._execute("/ppp/secret", "set", id=s[".id"], disabled="no")
                logger.info(f"PPPoE Secret habilitado: {name}")
                return {"action": "pppoe_secret_enabled", "name": name}

        return {"action": "pppoe_secret_not_found", "name": name}

    async def list_pppoe_secrets(self) -> List[Dict[str, Any]]:
        """Lista todos los PPPoE Secrets."""
        return await self._execute("/ppp/secret")

    async def get_active_pppoe_connections(self) -> List[Dict[str, Any]]:
        """Lista conexiones PPPoE activas (clientes conectados ahora)."""
        return await self._execute("/ppp/active")

    # ================================================================
    # SIMPLE QUEUES (CONTROL DE VELOCIDAD)
    # ================================================================

    async def create_simple_queue(
        self,
        name: str,
        target: str,
        max_limit_upload: str,
        max_limit_download: str,
        burst_limit: str = "",
        burst_threshold: str = "",
        burst_time: str = "",
        comment: str = "",
        disabled: bool = False
    ) -> Dict[str, Any]:
        """
        Crea una Simple Queue para control de velocidad.
        
        Args:
            name: Nombre de la queue (ej: "queue_jcarlos_fibra")
            target: IP del cliente (ej: "10.10.10.100/32")
            max_limit_upload: Velocidad subida (ej: "25M")
            max_limit_download: Velocidad bajada (ej: "50M")
            burst_limit: Burst upload/download (ej: "30M/60M")
            burst_threshold: Threshold (ej: "20M/40M")
            burst_time: Tiempo burst (ej: "10/10")
            comment: Comentario
        """
        params = {
            "name": name,
            "target": target if "/" in target else f"{target}/32",
            "max-limit": f"{max_limit_upload}/{max_limit_download}",
            "comment": comment,
            "disabled": "yes" if disabled else "no"
        }
        if burst_limit:
            params["burst-limit"] = burst_limit
        if burst_threshold:
            params["burst-threshold"] = burst_threshold
        if burst_time:
            params["burst-time"] = burst_time

        logger.info(f"Creando Queue: {name} → {target} ({max_limit_upload}/{max_limit_download})")
        result = await self._execute("/queue/simple", "add", **params)
        return {"action": "queue_created", "name": name, "target": target, "result": result}

    async def delete_simple_queue(self, name: str) -> Dict[str, Any]:
        """Elimina una Simple Queue por nombre."""
        queues = await self._execute("/queue/simple")
        for q in queues:
            if q.get("name") == name:
                await self._execute("/queue/simple", "remove", id=q[".id"])
                logger.info(f"Queue eliminada: {name}")
                return {"action": "queue_deleted", "name": name}

        return {"action": "queue_not_found", "name": name}

    async def update_simple_queue(
        self,
        name: str,
        max_limit_upload: str = None,
        max_limit_download: str = None
    ) -> Dict[str, Any]:
        """Actualiza velocidad de una Queue existente."""
        queues = await self._execute("/queue/simple")
        for q in queues:
            if q.get("name") == name:
                params = {"id": q[".id"]}
                if max_limit_upload and max_limit_download:
                    params["max-limit"] = f"{max_limit_upload}/{max_limit_download}"
                await self._execute("/queue/simple", "set", **params)
                return {"action": "queue_updated", "name": name}

        return {"action": "queue_not_found", "name": name}

    async def disable_simple_queue(self, name: str) -> Dict[str, Any]:
        """Deshabilita una queue (suspender)."""
        queues = await self._execute("/queue/simple")
        for q in queues:
            if q.get("name") == name:
                await self._execute("/queue/simple", "set", id=q[".id"], disabled="yes")
                return {"action": "queue_disabled", "name": name}
        return {"action": "queue_not_found", "name": name}

    async def enable_simple_queue(self, name: str) -> Dict[str, Any]:
        """Habilita una queue (reactivar)."""
        queues = await self._execute("/queue/simple")
        for q in queues:
            if q.get("name") == name:
                await self._execute("/queue/simple", "set", id=q[".id"], disabled="no")
                return {"action": "queue_enabled", "name": name}
        return {"action": "queue_not_found", "name": name}

    # ================================================================
    # ADDRESS LIST (MOROSOS / SUSPENSIÓN)
    # ================================================================

    async def add_to_address_list(
        self,
        list_name: str,
        address: str,
        comment: str = "",
        timeout: str = ""
    ) -> Dict[str, Any]:
        """
        Agrega una IP a un Address List.
        Usado para marcar morosos (ej: list="morosos", address="10.10.10.100").
        """
        params = {
            "list": list_name,
            "address": address,
            "comment": comment
        }
        if timeout:
            params["timeout"] = timeout

        logger.info(f"Agregando {address} a lista '{list_name}'")
        result = await self._execute("/ip/firewall/address-list", "add", **params)
        return {"action": "address_added", "list": list_name, "address": address, "result": result}

    async def remove_from_address_list(self, list_name: str, address: str) -> Dict[str, Any]:
        """Remueve una IP de un Address List."""
        entries = await self._execute("/ip/firewall/address-list")
        for entry in entries:
            if entry.get("list") == list_name and entry.get("address") == address:
                await self._execute("/ip/firewall/address-list", "remove", id=entry[".id"])
                logger.info(f"Removido {address} de lista '{list_name}'")
                return {"action": "address_removed", "list": list_name, "address": address}

        return {"action": "address_not_found", "list": list_name, "address": address}

    # ================================================================
    # INTERFACES (LECTURA)
    # ================================================================

    async def get_interfaces(self) -> List[Dict[str, Any]]:
        """Lista todas las interfaces del MikroTik."""
        return await self._execute("/interface")

    async def get_pppoe_server_interfaces(self) -> List[Dict[str, Any]]:
        """Lista los PPPoE Servers configurados."""
        return await self._execute("/interface/pppoe-server/server")

    # ================================================================
    # IP ADDRESSES
    # ================================================================

    async def get_ip_addresses(self) -> List[Dict[str, Any]]:
        """Lista todas las IPs configuradas en el router."""
        return await self._execute("/ip/address")

    async def add_ip_address(
        self,
        address: str,
        interface: str,
        comment: str = "",
        disabled: bool = False
    ) -> Dict[str, Any]:
        """Agrega una IP a una interfaz."""
        params = {
            "address": address,
            "interface": interface,
            "comment": comment,
            "disabled": "yes" if disabled else "no"
        }
        result = await self._execute("/ip/address", "add", **params)
        return {"action": "ip_added", "address": address, "interface": interface, "result": result}

    # ================================================================
    # PPP PROFILES (PERFILES DE VELOCIDAD)
    # ================================================================

    async def list_ppp_profiles(self) -> List[Dict[str, Any]]:
        """Lista los perfiles PPP (controlan velocidad en PPPoE)."""
        return await self._execute("/ppp/profile")

    async def create_ppp_profile(
        self,
        name: str,
        rate_limit: str,
        local_address: str = "",
        dns_server: str = "",
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Crea un perfil PPP que controla la velocidad.
        
        Args:
            name: Nombre del perfil (ej: "50M-25M")
            rate_limit: Límite upload/download (ej: "25M/50M")
            local_address: IP local del server
            dns_server: DNS para los clientes
        """
        params = {
            "name": name,
            "rate-limit": rate_limit,
            "comment": comment
        }
        if local_address:
            params["local-address"] = local_address
        if dns_server:
            params["dns-server"] = dns_server

        result = await self._execute("/ppp/profile", "add", **params)
        return {"action": "ppp_profile_created", "name": name, "rate_limit": rate_limit, "result": result}
    
    # ================================================================
    # DHCP LEASES (FIBRA DHCP)
    # ================================================================

    async def list_dhcp_leases(self) -> List[Dict[str, Any]]:
        """Lista todos los DHCP Leases del MikroTik."""
        return await self._execute("/ip/dhcp-server/lease")

    async def create_dhcp_lease(
        self,
        mac_address: str,
        ip_address: str,
        server: str = "dhcp1",
        comment: str = "",
        disabled: bool = False
    ) -> Dict[str, Any]:
        """
        Crea un DHCP Lease estático (reserva IP por MAC).
        Equivale a: /ip dhcp-server lease add mac-address=XX:XX address=10.0.0.5

        Args:
            mac_address: MAC de la ONU/CPE del cliente (ej: "AA:BB:CC:DD:EE:FF")
            ip_address: IP fija que se le asigna (ej: "10.10.10.50")
            server: Nombre del DHCP server (ej: "dhcp1")
            comment: Comentario identificador
        """
        params = {
            "mac-address": mac_address.upper(),
            "address": ip_address,
            "server": server,
            "comment": comment,
            "disabled": "yes" if disabled else "no"
        }

        logger.info(f"Creando DHCP Lease: {mac_address} → {ip_address}")
        result = await self._execute("/ip/dhcp-server/lease", "add", **params)
        return {"action": "dhcp_lease_created", "mac": mac_address, "ip": ip_address, "result": result}

    async def delete_dhcp_lease(self, mac_address: str) -> Dict[str, Any]:
        """Elimina un DHCP Lease por MAC address."""
        leases = await self._execute("/ip/dhcp-server/lease")
        mac_upper = mac_address.upper()
        for lease in leases:
            if lease.get("mac-address", "").upper() == mac_upper:
                await self._execute("/ip/dhcp-server/lease", "remove", id=lease[".id"])
                logger.info(f"DHCP Lease eliminado: {mac_address}")
                return {"action": "dhcp_lease_deleted", "mac": mac_address}

        return {"action": "dhcp_lease_not_found", "mac": mac_address}

    async def disable_dhcp_lease(self, mac_address: str) -> Dict[str, Any]:
        """Deshabilita un DHCP Lease (suspender cliente DHCP)."""
        leases = await self._execute("/ip/dhcp-server/lease")
        mac_upper = mac_address.upper()
        for lease in leases:
            if lease.get("mac-address", "").upper() == mac_upper:
                await self._execute("/ip/dhcp-server/lease", "set", id=lease[".id"], disabled="yes")
                logger.info(f"DHCP Lease deshabilitado: {mac_address}")
                return {"action": "dhcp_lease_disabled", "mac": mac_address}

        return {"action": "dhcp_lease_not_found", "mac": mac_address}

    async def enable_dhcp_lease(self, mac_address: str) -> Dict[str, Any]:
        """Habilita un DHCP Lease (reactivar cliente DHCP)."""
        leases = await self._execute("/ip/dhcp-server/lease")
        mac_upper = mac_address.upper()
        for lease in leases:
            if lease.get("mac-address", "").upper() == mac_upper:
                await self._execute("/ip/dhcp-server/lease", "set", id=lease[".id"], disabled="no")
                logger.info(f"DHCP Lease habilitado: {mac_address}")
                return {"action": "dhcp_lease_enabled", "mac": mac_address}

        return {"action": "dhcp_lease_not_found", "mac": mac_address}

    async def get_dhcp_servers(self) -> List[Dict[str, Any]]:
        """Lista los DHCP Servers configurados en el MikroTik."""
        return await self._execute("/ip/dhcp-server")

    # ================================================================
    # OPERACIONES COMPUESTAS DHCP (ALTO NIVEL)
    # ================================================================

    async def provision_dhcp_client(
        self,
        mac_address: str,
        ip_address: str,
        upload_speed: str,
        download_speed: str,
        dhcp_server: str = "dhcp1",
        client_name: str = "",
        burst_upload: str = "",
        burst_download: str = "",
        burst_threshold_up: str = "",
        burst_threshold_down: str = "",
        burst_time: str = ""
    ) -> Dict[str, Any]:
        """
        Provisiona un cliente FIBRA DHCP completo en MikroTik:
        1. Crea DHCP Lease estático (MAC → IP fija)
        2. Crea Simple Queue (control de velocidad)

        Returns:
            Dict con resultados de ambas operaciones
        """
        results = {}
        comment = f"ISP-AUTO: {client_name}" if client_name else f"ISP-AUTO: {mac_address}"

        # 1. Crear DHCP Lease
        lease_result = await self.create_dhcp_lease(
            mac_address=mac_address,
            ip_address=ip_address,
            server=dhcp_server,
            comment=comment
        )
        results["dhcp_lease"] = lease_result

        # 2. Crear Simple Queue
        queue_name = f"queue_dhcp_{ip_address.replace('.', '_')}"
        burst_lim = f"{burst_upload}/{burst_download}" if burst_upload else ""
        burst_thr = f"{burst_threshold_up}/{burst_threshold_down}" if burst_threshold_up else ""

        queue_result = await self.create_simple_queue(
            name=queue_name,
            target=ip_address,
            max_limit_upload=upload_speed,
            max_limit_download=download_speed,
            burst_limit=burst_lim,
            burst_threshold=burst_thr,
            burst_time=burst_time,
            comment=comment
        )
        results["queue"] = queue_result

        logger.info(f"Cliente DHCP provisionado: {mac_address} → {ip_address}")
        return results

    async def deprovision_dhcp_client(self, mac_address: str, ip_address: str = "") -> Dict[str, Any]:
        """
        Elimina un cliente DHCP del MikroTik:
        1. Elimina DHCP Lease
        2. Elimina Simple Queue
        """
        results = {}

        # 1. Eliminar DHCP Lease
        results["dhcp_lease"] = await self.delete_dhcp_lease(mac_address)

        # 2. Eliminar Queue
        if ip_address:
            queue_name = f"queue_dhcp_{ip_address.replace('.', '_')}"
            results["queue"] = await self.delete_simple_queue(queue_name)

        logger.info(f"Cliente DHCP eliminado del MikroTik: {mac_address}")
        return results

    async def suspend_dhcp_client(self, mac_address: str, ip_address: str = "") -> Dict[str, Any]:
        """Suspende cliente DHCP: deshabilita lease + queue + agrega a morosos."""
        results = {}

        results["dhcp_lease"] = await self.disable_dhcp_lease(mac_address)

        if ip_address:
            queue_name = f"queue_dhcp_{ip_address.replace('.', '_')}"
            results["queue"] = await self.disable_simple_queue(queue_name)
            results["morosos"] = await self.add_to_address_list(
                list_name="morosos",
                address=ip_address,
                comment="Suspendido por sistema"
            )

        logger.info(f"Cliente DHCP suspendido: {mac_address}")
        return results

    async def reactivate_dhcp_client(self, mac_address: str, ip_address: str = "") -> Dict[str, Any]:
        """Reactiva cliente DHCP suspendido."""
        results = {}

        results["dhcp_lease"] = await self.enable_dhcp_lease(mac_address)

        if ip_address:
            queue_name = f"queue_dhcp_{ip_address.replace('.', '_')}"
            results["queue"] = await self.enable_simple_queue(queue_name)
            results["morosos"] = await self.remove_from_address_list("morosos", ip_address)

        logger.info(f"Cliente DHCP reactivado: {mac_address}")
        return results

    # ================================================================
    # OPERACIONES COMPUESTAS (ALTO NIVEL)
    # ================================================================

    async def provision_fiber_client(
        self,
        pppoe_username: str,
        pppoe_password: str,
        ip_address: str,
        upload_speed: str,
        download_speed: str,
        profile: str = "default",
        client_name: str = "",
        burst_upload: str = "",
        burst_download: str = "",
        burst_threshold_up: str = "",
        burst_threshold_down: str = "",
        burst_time: str = ""
    ) -> Dict[str, Any]:
        """
        Provisiona un cliente FIBRA completo en MikroTik:
        1. Crea PPPoE Secret (usuario + password + IP + perfil)
        2. Crea Simple Queue (control de velocidad)
        
        Returns:
            Dict con resultados de ambas operaciones
        """
        results = {}
        comment = f"ISP-AUTO: {client_name}" if client_name else f"ISP-AUTO: {pppoe_username}"

        # 1. Crear PPPoE Secret
        secret_result = await self.create_pppoe_secret(
            name=pppoe_username,
            password=pppoe_password,
            remote_address=ip_address,
            profile=profile,
            comment=comment
        )
        results["pppoe_secret"] = secret_result

        # 2. Crear Simple Queue
        queue_name = f"queue_{pppoe_username}"
        burst_lim = f"{burst_upload}/{burst_download}" if burst_upload else ""
        burst_thr = f"{burst_threshold_up}/{burst_threshold_down}" if burst_threshold_up else ""

        queue_result = await self.create_simple_queue(
            name=queue_name,
            target=ip_address,
            max_limit_upload=upload_speed,
            max_limit_download=download_speed,
            burst_limit=burst_lim,
            burst_threshold=burst_thr,
            burst_time=burst_time,
            comment=comment
        )
        results["queue"] = queue_result

        logger.info(f"Cliente FIBRA provisionado: {pppoe_username} → {ip_address}")
        return results

    async def provision_antenna_client(
        self,
        ip_address: str,
        upload_speed: str,
        download_speed: str,
        client_name: str = "",
        mac_address: str = "",
        burst_upload: str = "",
        burst_download: str = "",
        burst_threshold_up: str = "",
        burst_threshold_down: str = "",
        burst_time: str = ""
    ) -> Dict[str, Any]:
        """
        Provisiona un cliente ANTENA completo en MikroTik:
        1. Crea Simple Queue (control de velocidad por IP)
        2. (Opcional) Agrega a address-list de clientes activos
        
        Returns:
            Dict con resultados
        """
        results = {}
        queue_name = f"queue_{ip_address.replace('.', '_')}"
        comment = f"ISP-AUTO: {client_name}" if client_name else f"ISP-AUTO: {ip_address}"

        # 1. Crear Simple Queue
        burst_lim = f"{burst_upload}/{burst_download}" if burst_upload else ""
        burst_thr = f"{burst_threshold_up}/{burst_threshold_down}" if burst_threshold_up else ""

        queue_result = await self.create_simple_queue(
            name=queue_name,
            target=ip_address,
            max_limit_upload=upload_speed,
            max_limit_download=download_speed,
            burst_limit=burst_lim,
            burst_threshold=burst_thr,
            burst_time=burst_time,
            comment=comment
        )
        results["queue"] = queue_result

        # 2. Agregar a lista de clientes activos
        addr_result = await self.add_to_address_list(
            list_name="clientes_activos",
            address=ip_address,
            comment=comment
        )
        results["address_list"] = addr_result

        logger.info(f"Cliente ANTENA provisionado: {ip_address}")
        return results

    async def deprovision_fiber_client(
        self,
        pppoe_username: str,
        ip_address: str = ""
    ) -> Dict[str, Any]:
        """
        Elimina un cliente FIBRA del MikroTik:
        1. Elimina PPPoE Secret
        2. Elimina Simple Queue
        """
        results = {}

        # 1. Eliminar PPPoE Secret
        results["pppoe_secret"] = await self.delete_pppoe_secret(pppoe_username)

        # 2. Eliminar Queue
        queue_name = f"queue_{pppoe_username}"
        results["queue"] = await self.delete_simple_queue(queue_name)

        # 3. Remover de address-list si existe
        if ip_address:
            results["address_list"] = await self.remove_from_address_list(
                "clientes_activos", ip_address
            )

        logger.info(f"Cliente FIBRA eliminado del MikroTik: {pppoe_username}")
        return results

    async def deprovision_antenna_client(self, ip_address: str) -> Dict[str, Any]:
        """
        Elimina un cliente ANTENA del MikroTik:
        1. Elimina Simple Queue
        2. Remueve de address-list
        """
        results = {}

        queue_name = f"queue_{ip_address.replace('.', '_')}"
        results["queue"] = await self.delete_simple_queue(queue_name)
        results["address_list"] = await self.remove_from_address_list(
            "clientes_activos", ip_address
        )

        logger.info(f"Cliente ANTENA eliminado del MikroTik: {ip_address}")
        return results

    async def suspend_client(
        self,
        pppoe_username: str = None,
        ip_address: str = None,
        connection_type: str = "fiber"
    ) -> Dict[str, Any]:
        """
        Suspende un cliente (por falta de pago, etc).
        FIBRA: Deshabilita PPPoE Secret + Queue + Agrega a morosos
        ANTENA: Deshabilita Queue + Agrega a morosos
        """
        results = {}

        if connection_type == "fiber" and pppoe_username:
            results["pppoe"] = await self.disable_pppoe_secret(pppoe_username)
            queue_name = f"queue_{pppoe_username}"
            results["queue"] = await self.disable_simple_queue(queue_name)

        elif connection_type == "antenna" and ip_address:
            queue_name = f"queue_{ip_address.replace('.', '_')}"
            results["queue"] = await self.disable_simple_queue(queue_name)

        if ip_address:
            results["morosos"] = await self.add_to_address_list(
                list_name="morosos",
                address=ip_address,
                comment="Suspendido por sistema"
            )

        logger.info(f"Cliente suspendido: {pppoe_username or ip_address}")
        return results

    async def reactivate_client(
        self,
        pppoe_username: str = None,
        ip_address: str = None,
        connection_type: str = "fiber"
    ) -> Dict[str, Any]:
        """
        Reactiva un cliente suspendido.
        """
        results = {}

        if connection_type == "fiber" and pppoe_username:
            results["pppoe"] = await self.enable_pppoe_secret(pppoe_username)
            queue_name = f"queue_{pppoe_username}"
            results["queue"] = await self.enable_simple_queue(queue_name)

        elif connection_type == "antenna" and ip_address:
            queue_name = f"queue_{ip_address.replace('.', '_')}"
            results["queue"] = await self.enable_simple_queue(queue_name)

        if ip_address:
            results["morosos"] = await self.remove_from_address_list("morosos", ip_address)

        logger.info(f"Cliente reactivado: {pppoe_username or ip_address}")
        return results