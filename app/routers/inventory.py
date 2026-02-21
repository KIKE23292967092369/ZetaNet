"""
Sistema ISP - Router: Inventario
ONUs, CPEs, Routers, Proveedores, Marcas, Modelos.
Validación MAC única por tenant.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.dependencies import get_db, get_current_user
from app.models.inventory import (
    Brand, DeviceModel, Supplier, MerchandiseReception,
    Onu, Cpe, Router
)
from app.models.user import User
from app.schemas.inventory import (
    BrandCreate, BrandResponse,
    DeviceModelCreate, DeviceModelResponse,
    SupplierCreate, SupplierResponse,
    OnuCreate, OnuUpdate, OnuResponse, OnuListResponse,
    CpeCreate, CpeUpdate, CpeResponse, CpeListResponse,
    RouterCreate, RouterResponse
)

router = APIRouter(prefix="/inventory", tags=["Inventario"])


# ===== VALIDACIÓN MAC ÚNICA =====

async def check_mac_unique(db: AsyncSession, tenant_id: int, mac: str, exclude_table=None, exclude_id: int = None):
    """
    Verifica que una MAC no exista en ONUs ni CPEs del tenant.
    Si ya existe, lanza error con detalle de a quién está asignada.
    """
    mac_upper = mac.upper().strip()

    # Buscar en ONUs
    q_onu = select(Onu).where(Onu.tenant_id == tenant_id, Onu.mac_address == mac_upper)
    if exclude_table == "onus" and exclude_id:
        q_onu = q_onu.where(Onu.id != exclude_id)
    onu = (await db.execute(q_onu)).scalar_one_or_none()
    if onu:
        detail = f" (asignada a conexión {onu.connection_id})" if onu.connection_id else ""
        raise HTTPException(400, f"MAC {mac_upper} ya registrada en ONU ID {onu.id}{detail}")

    # Buscar en CPEs (mac_ether1)
    q_cpe = select(Cpe).where(Cpe.tenant_id == tenant_id, Cpe.mac_ether1 == mac_upper)
    if exclude_table == "cpes" and exclude_id:
        q_cpe = q_cpe.where(Cpe.id != exclude_id)
    cpe = (await db.execute(q_cpe)).scalar_one_or_none()
    if cpe:
        detail = f" (asignada a conexión {cpe.connection_id})" if cpe.connection_id else ""
        raise HTTPException(400, f"MAC {mac_upper} ya registrada en CPE ID {cpe.id}{detail}")


# ===== MARCAS =====

@router.get("/brands", response_model=List[BrandResponse])
async def list_brands(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Brand).where(Brand.tenant_id == user.tenant_id).order_by(Brand.name)
    )
    return result.scalars().all()


@router.post("/brands", response_model=BrandResponse, status_code=201)
async def create_brand(data: BrandCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    brand = Brand(tenant_id=user.tenant_id, name=data.name)
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand


# ===== MODELOS =====

@router.get("/models", response_model=List[DeviceModelResponse])
async def list_models(
    device_type: Optional[str] = None,
    brand_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(DeviceModel).where(DeviceModel.tenant_id == user.tenant_id)
    if device_type:
        q = q.where(DeviceModel.device_type == device_type)
    if brand_id:
        q = q.where(DeviceModel.brand_id == brand_id)
    result = await db.execute(q.order_by(DeviceModel.name))
    return result.scalars().all()


@router.post("/models", response_model=DeviceModelResponse, status_code=201)
async def create_model(data: DeviceModelCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    model = DeviceModel(tenant_id=user.tenant_id, **data.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


# ===== PROVEEDORES =====

@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Supplier).where(Supplier.tenant_id == user.tenant_id).order_by(Supplier.name)
    )
    return result.scalars().all()


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    supplier = Supplier(tenant_id=user.tenant_id, **data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


# ===== ONUs =====

@router.get("/onus", response_model=List[OnuResponse])
async def list_onus(
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(Onu).where(Onu.tenant_id == user.tenant_id, Onu.is_active == True)
    if available_only:
        q = q.where(Onu.connection_id == None)
    result = await db.execute(q.order_by(Onu.id.desc()))
    return result.scalars().all()


@router.post("/onus", response_model=OnuResponse, status_code=201)
async def create_onu(data: OnuCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Validar MAC única
    await check_mac_unique(db, user.tenant_id, data.mac_address)

    onu = Onu(tenant_id=user.tenant_id, **data.model_dump())
    onu.mac_address = data.mac_address.upper().strip()
    db.add(onu)
    await db.commit()
    await db.refresh(onu)
    return onu


@router.patch("/onus/{onu_id}", response_model=OnuResponse)
async def update_onu(onu_id: int, data: OnuUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    onu = await db.get(Onu, onu_id)
    if not onu or onu.tenant_id != user.tenant_id:
        raise HTTPException(404, "ONU no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(onu, k, v)
    await db.commit()
    await db.refresh(onu)
    return onu


# ===== CPEs =====

@router.get("/cpes", response_model=List[CpeResponse])
async def list_cpes(
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(Cpe).where(Cpe.tenant_id == user.tenant_id, Cpe.is_active == True)
    if available_only:
        q = q.where(Cpe.connection_id == None)
    result = await db.execute(q.order_by(Cpe.id.desc()))
    return result.scalars().all()


@router.post("/cpes", response_model=CpeResponse, status_code=201)
async def create_cpe(data: CpeCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Validar MAC única
    await check_mac_unique(db, user.tenant_id, data.mac_ether1)

    cpe = Cpe(tenant_id=user.tenant_id, **data.model_dump())
    cpe.mac_ether1 = data.mac_ether1.upper().strip()
    # Auto-generar MAC WLAN si no se envía (lógica simplificada)
    if not data.mac_wlan:
        cpe.mac_wlan = data.mac_ether1.upper().strip()
    db.add(cpe)
    await db.commit()
    await db.refresh(cpe)
    return cpe


@router.patch("/cpes/{cpe_id}", response_model=CpeResponse)
async def update_cpe(cpe_id: int, data: CpeUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    cpe = await db.get(Cpe, cpe_id)
    if not cpe or cpe.tenant_id != user.tenant_id:
        raise HTTPException(404, "CPE no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cpe, k, v)
    await db.commit()
    await db.refresh(cpe)
    return cpe


# ===== ROUTERS =====

@router.get("/routers", response_model=List[RouterResponse])
async def list_routers(
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(Router).where(Router.tenant_id == user.tenant_id, Router.is_active == True)
    if available_only:
        q = q.where(Router.connection_id == None)
    result = await db.execute(q.order_by(Router.id.desc()))
    return result.scalars().all()


@router.post("/routers", response_model=RouterResponse, status_code=201)
async def create_router(data: RouterCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if data.mac_address:
        await check_mac_unique(db, user.tenant_id, data.mac_address)
    rtr = Router(tenant_id=user.tenant_id, **data.model_dump())
    if data.mac_address:
        rtr.mac_address = data.mac_address.upper().strip()
    db.add(rtr)
    await db.commit()
    await db.refresh(rtr)
    return rtr
