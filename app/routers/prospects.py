"""
Sistema ISP - Router: Prospectos
CRUD + seguimiento + convertir a cliente.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import date

from app.dependencies import get_db, get_current_user
from app.models.prospect import Prospect, ProspectStatus, ProspectFollowUp
from app.models.client import Client, ClientType, ClientStatus
from app.models.user import User
from app.schemas.prospect import (
    ProspectCreate, ProspectUpdate, ProspectResponse,
    ProspectDetailResponse, FollowUpCreate, FollowUpResponse
)

router = APIRouter(prefix="/prospects", tags=["Prospectos"])


@router.get("/", response_model=List[ProspectResponse])
async def list_prospects(
    status: Optional[ProspectStatus] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(Prospect).where(Prospect.tenant_id == user.tenant_id)
    if status:
        q = q.where(Prospect.status == status)
    q = q.order_by(Prospect.id.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=ProspectResponse, status_code=201)
async def create_prospect(
    data: ProspectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    prospect = Prospect(
        tenant_id=user.tenant_id,
        registered_by_id=user.id,
        **data.model_dump()
    )
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)
    return prospect


@router.get("/{prospect_id}", response_model=ProspectDetailResponse)
async def get_prospect(
    prospect_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    prospect = await db.get(Prospect, prospect_id)
    if not prospect or prospect.tenant_id != user.tenant_id:
        raise HTTPException(404, "Prospecto no encontrado")

    fups = await db.execute(
        select(ProspectFollowUp)
        .where(ProspectFollowUp.prospect_id == prospect_id)
        .order_by(ProspectFollowUp.created_at.desc())
    )

    return ProspectDetailResponse(
        **{k: v for k, v in prospect.__dict__.items() if not k.startswith("_")},
        follow_ups=[FollowUpResponse.model_validate(f) for f in fups.scalars().all()]
    )


@router.patch("/{prospect_id}", response_model=ProspectResponse)
async def update_prospect(
    prospect_id: int,
    data: ProspectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    prospect = await db.get(Prospect, prospect_id)
    if not prospect or prospect.tenant_id != user.tenant_id:
        raise HTTPException(404, "Prospecto no encontrado")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(prospect, k, v)

    await db.commit()
    await db.refresh(prospect)
    return prospect


# ===== SEGUIMIENTO =====

@router.post("/{prospect_id}/follow-up", response_model=FollowUpResponse, status_code=201)
async def add_follow_up(
    prospect_id: int,
    data: FollowUpCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    prospect = await db.get(Prospect, prospect_id)
    if not prospect or prospect.tenant_id != user.tenant_id:
        raise HTTPException(404, "Prospecto no encontrado")

    fup = ProspectFollowUp(
        tenant_id=user.tenant_id,
        prospect_id=prospect_id,
        user_id=user.id,
        note=data.note
    )
    db.add(fup)

    # Actualizar status a contacted si estaba pending
    if prospect.status == ProspectStatus.PENDING:
        prospect.status = ProspectStatus.CONTACTED

    await db.commit()
    await db.refresh(fup)
    return fup


# ===== CONVERTIR A CLIENTE =====

@router.post("/{prospect_id}/convert", response_model=dict)
async def convert_to_client(
    prospect_id: int,
    cut_day: int = Query(default=10, ge=1, le=31),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Convierte prospecto en cliente.
    Crea el registro en clients y marca el prospecto como converted.
    """
    prospect = await db.get(Prospect, prospect_id)
    if not prospect or prospect.tenant_id != user.tenant_id:
        raise HTTPException(404, "Prospecto no encontrado")
    if prospect.status == ProspectStatus.CONVERTED:
        raise HTTPException(400, "Prospecto ya fue convertido")

    # Crear cliente desde datos del prospecto
    client = Client(
        tenant_id=user.tenant_id,
        contract_date=date.today(),
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        locality=prospect.locality or "",
        address=prospect.address or "",
        phone_cell=prospect.phone,
        email=prospect.email,
        client_type=ClientType.CON_PLAN,
        cut_day=cut_day,
        status=ClientStatus.PENDING,
    )
    db.add(client)
    await db.flush()

    # Marcar prospecto como convertido
    prospect.status = ProspectStatus.CONVERTED
    prospect.converted_client_id = client.id

    await db.commit()
    return {
        "message": "Prospecto convertido a cliente",
        "client_id": client.id,
        "client_name": f"{client.first_name} {client.last_name}"
    }
