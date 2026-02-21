"""
Sistema ISP - Router: Planes de Servicio
CRUD + asignación a células bidireccional.
Al crear plan se configura automáticamente en MikroTik.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.dependencies import get_db, get_current_user
from app.models.plan import ServicePlan, PlanType, CellPlan
from app.models.connection import Connection
from app.models.user import User
from app.schemas.plan import (
    ServicePlanCreate, ServicePlanUpdate,
    ServicePlanResponse, ServicePlanListResponse
)

router = APIRouter(prefix="/plans", tags=["Planes de Servicio"])


@router.get("/", response_model=List[ServicePlanListResponse])
async def list_plans(
    plan_type: Optional[PlanType] = None,
    cell_id: Optional[int] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(ServicePlan).where(ServicePlan.tenant_id == user.tenant_id)
    if plan_type:
        q = q.where(ServicePlan.plan_type == plan_type)
    if is_active is not None:
        q = q.where(ServicePlan.is_active == is_active)
    if cell_id:
        q = q.join(CellPlan).where(CellPlan.cell_id == cell_id)
    q = q.order_by(ServicePlan.id)
    result = await db.execute(q)
    plans = result.scalars().all()

    responses = []
    for p in plans:
        conn_count = await db.scalar(
            select(func.count(Connection.id)).where(
                Connection.plan_id == p.id, Connection.is_active == True
            )
        ) or 0
        cell_count = await db.scalar(
            select(func.count(CellPlan.id)).where(CellPlan.plan_id == p.id)
        ) or 0
        responses.append(ServicePlanListResponse(
            id=p.id, name=p.name, plan_type=p.plan_type, price=float(p.price),
            upload_speed=p.upload_speed, download_speed=p.download_speed,
            priority=p.priority, tags=p.tags, is_active=p.is_active,
            connection_count=conn_count, cell_count=cell_count
        ))
    return responses


@router.post("/", response_model=ServicePlanResponse, status_code=201)
async def create_plan(
    data: ServicePlanCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    plan = ServicePlan(
        tenant_id=user.tenant_id,
        **data.model_dump(exclude={"cell_ids"})
    )
    db.add(plan)
    await db.flush()

    # Asignar a células
    for cid in (data.cell_ids or []):
        db.add(CellPlan(tenant_id=user.tenant_id, cell_id=cid, plan_id=plan.id))

    # TODO: Crear queue/profile en MikroTik

    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=ServicePlanResponse)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    plan = await db.get(ServicePlan, plan_id)
    if not plan or plan.tenant_id != user.tenant_id:
        raise HTTPException(404, "Plan no encontrado")
    return plan


@router.patch("/{plan_id}", response_model=ServicePlanResponse)
async def update_plan(
    plan_id: int,
    data: ServicePlanUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    plan = await db.get(ServicePlan, plan_id)
    if not plan or plan.tenant_id != user.tenant_id:
        raise HTTPException(404, "Plan no encontrado")

    updates = data.model_dump(exclude_unset=True, exclude={"cell_ids"})
    for k, v in updates.items():
        setattr(plan, k, v)

    if data.cell_ids is not None:
        existing = await db.execute(
            select(CellPlan).where(CellPlan.plan_id == plan_id)
        )
        for cp in existing.scalars().all():
            await db.delete(cp)
        for cid in data.cell_ids:
            db.add(CellPlan(tenant_id=user.tenant_id, cell_id=cid, plan_id=plan_id))

    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    plan = await db.get(ServicePlan, plan_id)
    if not plan or plan.tenant_id != user.tenant_id:
        raise HTTPException(404, "Plan no encontrado")

    # Verificar que no tenga conexiones activas
    count = await db.scalar(
        select(func.count(Connection.id)).where(
            Connection.plan_id == plan_id, Connection.is_active == True
        )
    )
    if count and count > 0:
        raise HTTPException(400, f"No se puede eliminar: {count} conexiones activas usan este plan")

    plan.is_active = False
    await db.commit()
    return {"message": "Plan desactivado"}
