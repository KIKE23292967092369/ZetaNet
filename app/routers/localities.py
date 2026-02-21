"""
NetKeeper - Router: Localidades
CRUD completo para catálogo de localidades.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.dependencies import get_db, get_current_user
from app.models.locality import Locality
from app.models.user import User
from app.schemas.locality import (
    LocalityCreate, LocalityUpdate, LocalityResponse
)

router = APIRouter(prefix="/localities", tags=["Localidades"])


@router.get("/", response_model=List[LocalityResponse])
async def list_localities(
    active_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista todas las localidades del tenant."""
    q = select(Locality).where(Locality.tenant_id == user.tenant_id)
    if active_only:
        q = q.where(Locality.is_active == True)
    q = q.order_by(Locality.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/", response_model=LocalityResponse, status_code=201)
async def create_locality(
    data: LocalityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Crea una nueva localidad."""
    locality = Locality(
        tenant_id=user.tenant_id,
        **data.model_dump()
    )
    db.add(locality)
    await db.commit()
    await db.refresh(locality)
    return locality


@router.get("/{locality_id}", response_model=LocalityResponse)
async def get_locality(
    locality_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Obtiene una localidad por ID."""
    locality = await db.get(Locality, locality_id)
    if not locality or locality.tenant_id != user.tenant_id:
        raise HTTPException(404, "Localidad no encontrada")
    return locality


@router.patch("/{locality_id}", response_model=LocalityResponse)
async def update_locality(
    locality_id: int,
    data: LocalityUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Actualiza una localidad."""
    locality = await db.get(Locality, locality_id)
    if not locality or locality.tenant_id != user.tenant_id:
        raise HTTPException(404, "Localidad no encontrada")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(locality, k, v)

    await db.commit()
    await db.refresh(locality)
    return locality


@router.delete("/{locality_id}")
async def delete_locality(
    locality_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Elimina una localidad (solo si no tiene clientes asignados)."""
    locality = await db.get(Locality, locality_id)
    if not locality or locality.tenant_id != user.tenant_id:
        raise HTTPException(404, "Localidad no encontrada")

    # Verificar si tiene clientes asignados
    from app.models.client import Client
    count = await db.execute(
        select(func.count()).where(
            Client.locality_id == locality_id,
            Client.tenant_id == user.tenant_id
        )
    )
    if count.scalar() > 0:
        raise HTTPException(400, "No se puede eliminar: tiene clientes asignados")

    await db.delete(locality)
    await db.commit()
    return {"message": "Localidad eliminada"}