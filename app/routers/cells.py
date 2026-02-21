"""
Sistema ISP - Router: Células
CRUD + config OLT + zonas/NAPs/puertos + cascada para conexiones.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.dependencies import get_db, get_current_user
from app.models.cell import Cell, CellType
from app.models.olt import OltConfig
from app.models.network import OltZone, Nap, NapPort
from app.models.plan import CellPlan, ServicePlan, CellInterface
from app.models.user import User
from app.schemas.cell import (
    CellCreate, CellUpdate, CellResponse, CellListResponse,
    OltConfigCreate, OltConfigResponse
)
from app.schemas.network import (
    OltZoneCreate, OltZoneUpdate, OltZoneResponse,
    NapCreate, NapUpdate, NapResponse, NapDetailResponse, NapPortResponse,
    CascadeZoneResponse, CascadeNapResponse, CascadeFreePortResponse
)
from app.schemas.plan import CellInterfaceResponse, CellInterfaceUpdate

router = APIRouter(prefix="/cells", tags=["Células"])


# ========== CRUD CÉLULAS ==========

@router.get("/", response_model=List[CellListResponse])
async def list_cells(
    cell_type: Optional[CellType] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(Cell).where(Cell.tenant_id == user.tenant_id)
    if cell_type:
        q = q.where(Cell.cell_type == cell_type)
    q = q.order_by(Cell.id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=CellResponse, status_code=201)
async def create_cell(
    data: CellCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    cell = Cell(tenant_id=user.tenant_id, **data.model_dump(exclude={"plan_ids"}))
    db.add(cell)
    await db.flush()

    # Asignar planes
    for pid in (data.plan_ids or []):
        db.add(CellPlan(tenant_id=user.tenant_id, cell_id=cell.id, plan_id=pid))

    # Si es FIBRA, crear NapPorts no se necesita aquí (se crean al crear NAPs)
    await db.commit()
    await db.refresh(cell)
    return cell


@router.get("/{cell_id}", response_model=CellResponse)
async def get_cell(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")
    return cell


@router.patch("/{cell_id}", response_model=CellResponse)
async def update_cell(
    cell_id: int,
    data: CellUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")

    updates = data.model_dump(exclude_unset=True, exclude={"plan_ids"})
    for k, v in updates.items():
        setattr(cell, k, v)

    # Actualizar planes si se envían
    if data.plan_ids is not None:
        # Borrar existentes
        existing = await db.execute(
            select(CellPlan).where(CellPlan.cell_id == cell_id)
        )
        for cp in existing.scalars().all():
            await db.delete(cp)
        # Crear nuevos
        for pid in data.plan_ids:
            db.add(CellPlan(tenant_id=user.tenant_id, cell_id=cell_id, plan_id=pid))

    await db.commit()
    await db.refresh(cell)
    return cell


# ========== OLT CONFIG (FIBRA) ==========

@router.post("/{cell_id}/olt", response_model=OltConfigResponse, status_code=201)
async def create_olt_config(
    cell_id: int,
    data: OltConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")
    if cell.cell_type not in [CellType.FIBRA, CellType.HIFIBER_IPOE]:
        raise HTTPException(400, "OLT solo aplica para células FIBRA")

    olt = OltConfig(tenant_id=user.tenant_id, cell_id=cell_id,
                    **data.model_dump(exclude={"cell_id"}))
    db.add(olt)
    await db.commit()
    await db.refresh(olt)
    return olt


@router.get("/{cell_id}/olt", response_model=OltConfigResponse)
async def get_olt_config(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(OltConfig).where(OltConfig.cell_id == cell_id, OltConfig.tenant_id == user.tenant_id)
    )
    olt = result.scalar_one_or_none()
    if not olt:
        raise HTTPException(404, "OLT no configurada")
    return olt


# ========== ZONAS OLT ==========

@router.get("/{cell_id}/zones", response_model=List[OltZoneResponse])
async def list_zones(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(OltZone).where(OltZone.cell_id == cell_id, OltZone.tenant_id == user.tenant_id)
        .order_by(OltZone.id)
    )
    return result.scalars().all()


@router.post("/{cell_id}/zones", response_model=OltZoneResponse, status_code=201)
async def create_zone(
    cell_id: int,
    data: OltZoneCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")

    zone = OltZone(tenant_id=user.tenant_id, cell_id=cell_id,
                   name=data.name, slot_port=data.slot_port)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


# ========== NAPs ==========

@router.post("/zones/{zone_id}/naps", response_model=NapResponse, status_code=201)
async def create_nap(
    zone_id: int,
    data: NapCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    zone = await db.get(OltZone, zone_id)
    if not zone or zone.tenant_id != user.tenant_id:
        raise HTTPException(404, "Zona OLT no encontrada")

    nap = Nap(tenant_id=user.tenant_id, olt_zone_id=zone_id,
              **data.model_dump(exclude={"olt_zone_id"}))
    db.add(nap)
    await db.flush()

    # Crear puertos automáticamente
    for i in range(1, data.total_ports + 1):
        db.add(NapPort(tenant_id=user.tenant_id, nap_id=nap.id, port_number=i))

    await db.commit()
    await db.refresh(nap)
    return nap


@router.get("/naps/{nap_id}", response_model=NapDetailResponse)
async def get_nap_detail(
    nap_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    nap = await db.get(Nap, nap_id)
    if not nap or nap.tenant_id != user.tenant_id:
        raise HTTPException(404, "NAP no encontrada")

    ports_result = await db.execute(
        select(NapPort).where(NapPort.nap_id == nap_id).order_by(NapPort.port_number)
    )
    ports = ports_result.scalars().all()
    occupied = sum(1 for p in ports if p.is_occupied)

    return NapDetailResponse(
        **{k: v for k, v in nap.__dict__.items() if not k.startswith("_")},
        ports=[NapPortResponse.model_validate(p) for p in ports],
        occupied_count=occupied,
        free_count=len(ports) - occupied
    )


# ========== CASCADA (para dropdowns de conexión FIBRA) ==========

@router.get("/{cell_id}/cascade/zones", response_model=List[CascadeZoneResponse])
async def cascade_zones(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Paso 1 cascada: Zonas OLT de una célula."""
    result = await db.execute(
        select(OltZone).where(
            OltZone.cell_id == cell_id,
            OltZone.tenant_id == user.tenant_id,
            OltZone.is_active == True
        ).order_by(OltZone.name)
    )
    zones = result.scalars().all()
    responses = []
    for z in zones:
        nap_count = await db.scalar(
            select(func.count(Nap.id)).where(Nap.olt_zone_id == z.id)
        )
        responses.append(CascadeZoneResponse(
            id=z.id, name=z.name, slot_port=z.slot_port, nap_count=nap_count or 0
        ))
    return responses


@router.get("/zones/{zone_id}/cascade/naps", response_model=List[CascadeNapResponse])
async def cascade_naps(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Paso 2 cascada: NAPs de una zona con puertos libres."""
    result = await db.execute(
        select(Nap).where(
            Nap.olt_zone_id == zone_id,
            Nap.tenant_id == user.tenant_id,
            Nap.is_active == True
        ).order_by(Nap.name)
    )
    naps = result.scalars().all()
    responses = []
    for n in naps:
        free = await db.scalar(
            select(func.count(NapPort.id)).where(
                NapPort.nap_id == n.id, NapPort.is_occupied == False
            )
        )
        responses.append(CascadeNapResponse(
            id=n.id, name=n.name, total_ports=n.total_ports, free_ports=free or 0
        ))
    return responses


@router.get("/naps/{nap_id}/cascade/ports", response_model=List[CascadeFreePortResponse])
async def cascade_free_ports(
    nap_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Paso 3 cascada: Solo puertos LIBRES de una NAP."""
    result = await db.execute(
        select(NapPort).where(
            NapPort.nap_id == nap_id,
            NapPort.is_occupied == False
        ).order_by(NapPort.port_number)
    )
    return result.scalars().all()


# ========== IP POOL ==========

@router.get("/{cell_id}/ip-pool")
async def get_ip_pool(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    from app.models.connection import Connection
    import ipaddress

    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")

    result = await db.execute(
        select(Connection.ip_address, Connection.id).where(
            Connection.cell_id == cell_id,
            Connection.tenant_id == user.tenant_id,
            Connection.ip_address != None
        )
    )
    used_ips = {r[0]: r[1] for r in result.fetchall()}

    available = []
    if cell.ipv4_range and cell.ipv4_mask:
        try:
            network = ipaddress.IPv4Network(f"{cell.ipv4_range}{cell.ipv4_mask}", strict=False)
            host_min = cell.ipv4_host_min or str(network.network_address + 1)
            host_max = cell.ipv4_host_max or str(network.broadcast_address - 1)
            min_int = int(ipaddress.IPv4Address(host_min))
            max_int = int(ipaddress.IPv4Address(host_max))
            for ip_int in range(min_int, max_int + 1):
                ip_str = str(ipaddress.IPv4Address(ip_int))
                available.append({
                    "ip": ip_str,
                    "available": ip_str not in used_ips
                })
        except Exception:
            pass

    return {
        "range": f"{cell.ipv4_range}{cell.ipv4_mask}" if cell.ipv4_range else None,
        "used": list(used_ips.keys()),
        "pool": available,
        "total": len(available),
        "free": sum(1 for ip in available if ip["available"]),
        "occupied": sum(1 for ip in available if not ip["available"]),
    }

# ========== INTERFACES (ANTENAS) ==========

@router.get("/{cell_id}/interfaces", response_model=List[CellInterfaceResponse])
async def list_interfaces(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(CellInterface).where(
            CellInterface.cell_id == cell_id,
            CellInterface.tenant_id == user.tenant_id
        ).order_by(CellInterface.interface_name)
    )
    return result.scalars().all()


@router.patch("/interfaces/{interface_id}", response_model=CellInterfaceResponse)
async def toggle_interface(
    interface_id: int,
    data: CellInterfaceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    iface = await db.get(CellInterface, interface_id)
    if not iface or iface.tenant_id != user.tenant_id:
        raise HTTPException(404, "Interface no encontrada")
    iface.connections_allowed = data.connections_allowed
    await db.commit()
    await db.refresh(iface)
    return iface

# ========== IP POOL POR INTERFAZ (MikroTik live + BD) ==========

@router.get("/{cell_id}/ip-pool-by-interface")
async def get_ip_pool_by_interface(
    cell_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    from app.models.connection import Connection
    from app.models.client import Client
    from app.services.mikrotik_helper import get_mikrotik_for_cell
    from app.services.mikrotik_service import MikroTikError
    import ipaddress

    cell = await db.get(Cell, cell_id)
    if not cell or cell.tenant_id != user.tenant_id:
        raise HTTPException(404, "Célula no encontrada")
    if not cell.mikrotik_host:
        raise HTTPException(400, "Célula sin MikroTik configurado")

    # 1. Leer IPs del MikroTik por interfaz
    try:
        mk = await get_mikrotik_for_cell(db, cell_id, user.tenant_id)
        mk_ips = await mk.get_ip_addresses()
    except MikroTikError as e:
        raise HTTPException(502, f"Error MikroTik: {e}")

    # 2. Cargar conexiones activas de esta célula con nombre del cliente
    result = await db.execute(
        select(
            Connection.ip_address,
            Connection.pppoe_username,
            Connection.status,
            Connection.connection_type,
            Client.name.label("client_name"),
            Client.id.label("client_id"),
        )
        .join(Client, Client.id == Connection.client_id)
        .where(
            Connection.cell_id == cell_id,
            Connection.tenant_id == user.tenant_id,
            Connection.ip_address != None,
            Connection.is_active == True,
        )
    )
    rows = result.fetchall()
    # Mapa ip → info cliente
    ip_map = {
        r.ip_address: {
            "client_name": r.client_name,
            "client_id":   r.client_id,
            "pppoe_username": r.pppoe_username,
            "status":      r.status.value,
            "type":        r.connection_type.value,
        }
        for r in rows
    }

    # 3. Por cada IP del MikroTik, calcular rango y cruzar
    interfaces_result = []
    for mk_ip in mk_ips:
        address_cidr = mk_ip.get("address", "")   # ej: "172.168.10.1/24"
        interface    = mk_ip.get("interface", "")
        disabled     = mk_ip.get("disabled", "false") == "true"

        if not address_cidr or "/" not in address_cidr:
            continue
        try:
            network  = ipaddress.IPv4Network(address_cidr, strict=False)
            # Excluir network address y broadcast
            all_hosts = [str(h) for h in network.hosts()]
        except Exception:
            continue

        ips = []
        used = 0
        for ip_str in all_hosts:
            info = ip_map.get(ip_str)
            if info:
                used += 1
                ips.append({
                    "address":      ip_str,
                    "used":         True,
                    "client_name":  info["client_name"],
                    "client_id":    info["client_id"],
                    "pppoe_username": info["pppoe_username"],
                    "status":       info["status"],
                })
            else:
                ips.append({
                    "address":     ip_str,
                    "used":        False,
                    "client_name": None,
                    "client_id":   None,
                    "pppoe_username": None,
                    "status":      None,
                })

        interfaces_result.append({
            "interface":  interface,
            "cidr":       address_cidr,
            "network":    str(network.network_address),
            "mask":       f"/{network.prefixlen}",
            "total":      len(all_hosts),
            "used":       used,
            "available":  len(all_hosts) - used,
            "disabled":   disabled,
            "ips":        ips,
        })

    return {"cell_id": cell_id, "interfaces": interfaces_result}