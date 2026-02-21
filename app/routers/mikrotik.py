"""
Sistema ISP - Router: MikroTik Management
Endpoints para gestionar MikroTik directamente desde la plataforma.
Test de conexión, listar secrets, queues, interfaces, etc.
"""
import ipaddress
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.cell import Cell
from app.services.mikrotik_service import MikroTikService, MikroTikError
from app.services.mikrotik_helper import get_mikrotik_for_cell

router = APIRouter(prefix="/mikrotik", tags=["MikroTik"])


# ================================================================
# SCHEMAS
# ================================================================

class ReadInterfacesRequest(BaseModel):
    host: str
    username: str
    password: str
    port: int = 8728
    use_ssl: bool = False


# ================================================================
# TEST DE CONEXIÓN
# ================================================================

@router.get("/test/{cell_id}")
async def test_mikrotik_connection(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Prueba la conexión al MikroTik de una célula.
    Retorna info del router: versión, uptime, CPU, memoria.
    """
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        result = await mk.test_connection()
        return result
    except MikroTikError as e:
        return {"connected": False, "error": str(e)}


@router.get("/identity/{cell_id}")
async def get_mikrotik_identity(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Obtiene el identity (nombre) del MikroTik."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        name = await mk.get_identity()
        return {"identity": name}
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# INTERFACES
# ================================================================

@router.get("/interfaces/{cell_id}")
async def list_interfaces(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista todas las interfaces del MikroTik de una célula."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        interfaces = await mk.get_interfaces()
        return {
            "cell_id": cell_id,
            "total": len(interfaces),
            "interfaces": [
                {
                    "name":        iface.get("name"),
                    "type":        iface.get("type"),
                    "mac_address": iface.get("mac-address"),
                    "running":     iface.get("running", "false"),
                    "disabled":    iface.get("disabled", "false"),
                    "tx_byte":     iface.get("tx-byte", "0"),
                    "rx_byte":     iface.get("rx-byte", "0"),
                    "comment":     iface.get("comment", "")
                }
                for iface in interfaces
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# PPPoE SECRETS
# ================================================================

@router.get("/pppoe-secrets/{cell_id}")
async def list_pppoe_secrets(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista todos los PPPoE Secrets del MikroTik de una célula."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        secrets = await mk.list_pppoe_secrets()
        return {
            "cell_id": cell_id,
            "total": len(secrets),
            "secrets": [
                {
                    "name":           s.get("name"),
                    "service":        s.get("service"),
                    "profile":        s.get("profile"),
                    "remote_address": s.get("remote-address"),
                    "local_address":  s.get("local-address", ""),
                    "disabled":       s.get("disabled", "false"),
                    "comment":        s.get("comment", "")
                }
                for s in secrets
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


@router.get("/pppoe-active/{cell_id}")
async def list_active_pppoe(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista conexiones PPPoE activas (clientes conectados ahora)."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        active = await mk.get_active_pppoe_connections()
        return {
            "cell_id": cell_id,
            "total": len(active),
            "active_connections": [
                {
                    "name":      a.get("name"),
                    "service":   a.get("service"),
                    "caller_id": a.get("caller-id"),
                    "address":   a.get("address"),
                    "uptime":    a.get("uptime"),
                    "encoding":  a.get("encoding", "")
                }
                for a in active
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# QUEUES
# ================================================================

@router.get("/queues/{cell_id}")
async def list_queues(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista Simple Queues del MikroTik."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        queues = await mk._execute("/queue/simple")
        return {
            "cell_id": cell_id,
            "total": len(queues),
            "queues": [
                {
                    "name":        q.get("name"),
                    "target":      q.get("target"),
                    "max_limit":   q.get("max-limit"),
                    "burst_limit": q.get("burst-limit", ""),
                    "disabled":    q.get("disabled", "false"),
                    "comment":     q.get("comment", "")
                }
                for q in queues
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# PPP PROFILES
# ================================================================

@router.get("/ppp-profiles/{cell_id}")
async def list_ppp_profiles(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista los perfiles PPP (controlan velocidad)."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        profiles = await mk.list_ppp_profiles()
        return {
            "cell_id": cell_id,
            "total": len(profiles),
            "profiles": [
                {
                    "name":          p.get("name"),
                    "rate_limit":    p.get("rate-limit", ""),
                    "local_address": p.get("local-address", ""),
                    "dns_server":    p.get("dns-server", ""),
                    "comment":       p.get("comment", "")
                }
                for p in profiles
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# IP ADDRESSES
# ================================================================

@router.get("/ip-addresses/{cell_id}")
async def list_ip_addresses(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista las IPs configuradas en el MikroTik."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        ips = await mk.get_ip_addresses()
        return {
            "cell_id": cell_id,
            "total": len(ips),
            "addresses": [
                {
                    "address":   ip.get("address"),
                    "network":   ip.get("network"),
                    "interface": ip.get("interface"),
                    "disabled":  ip.get("disabled", "false"),
                    "comment":   ip.get("comment", "")
                }
                for ip in ips
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# ADDRESS LISTS
# ================================================================

@router.get("/address-list/{cell_id}")
async def list_address_lists(
    cell_id: int,
    list_name: Optional[str] = Query(None, description="Filtrar por nombre de lista"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista entries de Address Lists del firewall."""
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        entries = await mk._execute("/ip/firewall/address-list")

        if list_name:
            entries = [e for e in entries if e.get("list") == list_name]

        return {
            "cell_id": cell_id,
            "total": len(entries),
            "entries": [
                {
                    "list":     e.get("list"),
                    "address":  e.get("address"),
                    "disabled": e.get("disabled", "false"),
                    "comment":  e.get("comment", ""),
                    "timeout":  e.get("timeout", "")
                }
                for e in entries
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# OPERACIONES MANUALES
# ================================================================

@router.post("/suspend-client")
async def suspend_client_manual(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Suspende un cliente manualmente en el MikroTik.
    Deshabilita su PPPoE Secret/Queue y lo agrega a lista de morosos.
    """
    from app.models.connection import Connection, ConnectionStatus
    conn = await db.get(Connection, connection_id)
    if not conn or conn.tenant_id != user.tenant_id:
        raise HTTPException(404, "Conexión no encontrada")

    try:
        mk = await get_mikrotik_for_cell(db, conn.cell_id, user.tenant_id)
        result = await mk.suspend_client(
            pppoe_username=conn.pppoe_username,
            ip_address=conn.ip_address,
            connection_type=conn.connection_type.value
        )
        conn.status = ConnectionStatus.SUSPENDED
        await db.commit()
        return {"message": "Cliente suspendido", "mikrotik_result": result}
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


@router.post("/reactivate-client")
async def reactivate_client_manual(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Reactiva un cliente suspendido en el MikroTik.
    Habilita su PPPoE Secret/Queue y lo remueve de morosos.
    """
    from app.models.connection import Connection, ConnectionStatus
    conn = await db.get(Connection, connection_id)
    if not conn or conn.tenant_id != user.tenant_id:
        raise HTTPException(404, "Conexión no encontrada")
    if conn.status != ConnectionStatus.SUSPENDED:
        raise HTTPException(400, "La conexión no está suspendida")

    try:
        mk = await get_mikrotik_for_cell(db, conn.cell_id, user.tenant_id)
        result = await mk.reactivate_client(
            pppoe_username=conn.pppoe_username,
            ip_address=conn.ip_address,
            connection_type=conn.connection_type.value
        )
        conn.status = ConnectionStatus.ACTIVE
        await db.commit()
        return {"message": "Cliente reactivado", "mikrotik_result": result}
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# LEER INTERFACES CON CREDENCIALES DIRECTAS (sin cell_id)
# Para usar al CREAR una célula nueva antes de guardarla
# ================================================================

@router.post("/read-interfaces")
async def read_interfaces_direct(
    creds: ReadInterfacesRequest,
    user: User = Depends(get_current_user)
):
    """
    Lee interfaces de un MikroTik con credenciales directas.
    Usado al crear una célula nueva (sin cell_id aún).
    """
    try:
        mk = MikroTikService(
            host=creds.host,
            username=creds.username,
            password=creds.password,
            port=creds.port
        )
        interfaces = await mk.get_interfaces()
        return {
            "interfaces": [
                {
                    "name":    iface.get("name"),
                    "type":    iface.get("type", ""),
                    "running": iface.get("running", "false") != "false",
                    "comment": iface.get("comment", "")
                }
                for iface in interfaces
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"No se pudo conectar al MikroTik: {e}")


# ================================================================
# SYSTEM INFO CON CREDENCIALES DIRECTAS
# Para el módulo Nodos de Red
# ================================================================

@router.post("/system-info")
async def get_system_info(
    creds: ReadInterfacesRequest,
    user: User = Depends(get_current_user)
):
    """
    Retorna info del sistema: CPU, RAM, uptime, modelo, interfaces con IPs.
    Usado en Nodos de Red al conectar al MikroTik.
    """
    try:
        mk = MikroTikService(
            host=creds.host,
            username=creds.username,
            password=creds.password,
            port=creds.port
        )
        info       = await mk.test_connection()
        identity   = await mk.get_identity()
        interfaces = await mk.get_interfaces()
        ips        = await mk.get_ip_addresses()

        # Agrupar IPs por interfaz
        ips_by_iface: dict = {}
        for ip in ips:
            iface = ip.get("interface", "")
            if iface not in ips_by_iface:
                ips_by_iface[iface] = []
            ips_by_iface[iface].append({
                "address":  ip.get("address"),
                "network":  ip.get("network"),
                "disabled": ip.get("disabled", "false") == "true"
            })

        return {
            "connected":    True,
            "identity":     identity,
            "host":         creds.host,
            "version":      info.get("version"),
            "board_name":   info.get("board_name"),
            "uptime":       info.get("uptime"),
            "cpu_load":     info.get("cpu_load"),
            "free_memory":  info.get("free_memory"),
            "total_memory": info.get("total_memory"),
            "interfaces": [
                {
                    "name":     iface.get("name"),
                    "type":     iface.get("type", ""),
                    "running":  iface.get("running", "false") != "false",
                    "disabled": iface.get("disabled", "false") == "true",
                    "comment":  iface.get("comment", ""),
                    "ips":      ips_by_iface.get(iface.get("name"), [])
                }
                for iface in interfaces
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"No se pudo conectar: {e}")


# ================================================================
# TRAFFIC SNAPSHOT CON CREDENCIALES DIRECTAS
# Polling cada 3s desde el frontend para tráfico en vivo
# ================================================================

@router.post("/traffic-snapshot")
async def get_traffic_snapshot(
    creds: ReadInterfacesRequest,
    user: User = Depends(get_current_user)
):
    """
    Snapshot del tráfico tx/rx por interfaz.
    El frontend hace polling cada 3s para simular tiempo real.
    """
    try:
        mk = MikroTikService(
            host=creds.host,
            username=creds.username,
            password=creds.password,
            port=creds.port
        )
        interfaces = await mk.get_interfaces()
        return {
            "interfaces": [
                {
                    "name":    iface.get("name"),
                    "tx_byte": int(iface.get("tx-byte", 0)),
                    "rx_byte": int(iface.get("rx-byte", 0)),
                    "tx_drop": int(iface.get("tx-drop", 0)),
                    "rx_drop": int(iface.get("rx-drop", 0)),
                    "running": iface.get("running", "false") != "false",
                }
                for iface in interfaces
            ]
        }
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")


# ================================================================
# IP POOL EN VIVO — interfaces + IPs ocupadas/libres con clientes
# Para Nodos de Red después de conectar al MikroTik
# ================================================================

@router.post("/ip-pool-live")
async def get_ip_pool_live(
    creds: ReadInterfacesRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Conecta al MikroTik con credenciales directas y retorna por interfaz:
    - Rango IPv4 con CIDR
    - Cada IP: ocupada (nombre cliente, estado, PPPoE) o libre
    Cruza con conexiones en BD filtrando por mikrotik_host.
    """
    from app.models.connection import Connection, ConnectionStatus
    from app.models.client import Client

    # 1. Conectar al MikroTik y leer interfaces + IPs configuradas
    try:
        mk = MikroTikService(
            host=creds.host,
            username=creds.username,
            password=creds.password,
            port=creds.port,
        )
        interfaces   = await mk.get_interfaces()
        ip_addresses = await mk.get_ip_addresses()
    except MikroTikError as e:
        raise HTTPException(502, f"No se pudo conectar al MikroTik: {e}")

    # 2. Agrupar CIDRs por interfaz  ej: {"bridge1": ["192.168.10.1/24"]}
    ips_by_iface: dict[str, list[str]] = {}
    for ip in ip_addresses:
        iface = ip.get("interface", "")
        if iface not in ips_by_iface:
            ips_by_iface[iface] = []
        ips_by_iface[iface].append(ip.get("address", ""))

    # 3. Consultar conexiones activas/suspendidas de este host en BD
    stmt = (
        select(Connection)
        .join(Cell,   Connection.cell_id   == Cell.id)
        .join(Client, Connection.client_id == Client.id)
        .where(
            Cell.mikrotik_host           == creds.host,
            Connection.tenant_id         == user.tenant_id,
            Connection.ip_address.isnot(None),
            Connection.status            != ConnectionStatus.CANCELLED,
        )
        .options(selectinload(Connection.client))
    )
    result      = await db.execute(stmt)
    connections = result.scalars().all()

    # 4. Mapa rápido: ip_str → datos del cliente
    ip_map: dict[str, dict] = {
        conn.ip_address: {
            "client_name":     conn.client.full_name if conn.client else "—",
            "client_id":       conn.client_id,
            "connection_id":   conn.id,
            "status":          conn.status.value,
            "pppoe_username":  conn.pppoe_username or None,
            "connection_type": conn.connection_type.value,
        }
        for conn in connections
    }

    # 5. Construir respuesta por interfaz
    iface_pool = []
    for iface in interfaces:
        name       = iface.get("name")
        running    = iface.get("running", "false") != "false"
        iface_type = iface.get("type", "")
        comment    = iface.get("comment", "")
        cidrs      = ips_by_iface.get(name, [])

        if not cidrs:
            iface_pool.append({
                "name": name, "type": iface_type,
                "running": running, "comment": comment,
                "has_pool": False, "cidrs": [],
            })
            continue

        pools = []
        for cidr in cidrs:
            try:
                network = ipaddress.IPv4Network(cidr, strict=False)
            except ValueError:
                continue

            all_ips  = list(network.hosts())
            total    = len(all_ips)
            occupied = 0
            ip_list  = []

            for ip_obj in all_ips:
                ip_str    = str(ip_obj)
                conn_data = ip_map.get(ip_str)
                if conn_data:
                    occupied += 1
                    ip_list.append({"ip": ip_str, "occupied": True, **conn_data})
                else:
                    ip_list.append({"ip": ip_str, "occupied": False})

            pools.append({
                "cidr":     cidr,
                "network":  str(network.network_address),
                "total":    total,
                "occupied": occupied,
                "free":     total - occupied,
                "pct_used": round(occupied / total * 100, 1) if total > 0 else 0,
                "ips":      ip_list,
            })

        iface_pool.append({
            "name":     name,
            "type":     iface_type,
            "running":  running,
            "comment":  comment,
            "has_pool": True,
            "cidrs":    pools,
        })

    # Interfaces con pool primero, luego ordenadas por nombre
    iface_pool.sort(key=lambda x: (not x["has_pool"], x["name"]))

    return {
        "host":                 creds.host,
        "total_interfaces":     len(iface_pool),
        "interfaces_with_pool": sum(1 for i in iface_pool if i["has_pool"]),
        "interfaces":           iface_pool,
    }