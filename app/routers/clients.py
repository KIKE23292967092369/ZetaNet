"""
Sistema ISP - Router de Clientes
CRUD completo de clientes/suscriptores del ISP.
Todos los queries filtran automáticamente por tenant_id.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.database import get_db
from app.dependencies import get_current_user, get_tenant_id
from app.models.user import User
from app.models.client import Client, ClientStatus
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse, ClientListResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])


@router.get("/")
async def list_clients(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=10000),
    search: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    client_type: str | None = None,
    locality_id: int | None = None,
    billing_group_id: int | None = None,
    has_balance: str | None = None,       # "yes" = con deuda, "no" = sin deuda
    broadcast_medium: str | None = None,
    cut_day: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista clientes del tenant con paginación, búsqueda y filtros avanzados."""
    tenant_id = current_user.tenant_id

    query = select(Client).where(Client.tenant_id == tenant_id, Client.is_active == True)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Client.first_name.ilike(search_term),
                Client.last_name.ilike(search_term),
                Client.phone_cell.ilike(search_term),
                Client.email.ilike(search_term),
                Client.locality.ilike(search_term),
            )
        )

    if status_filter:
        query = query.where(Client.status == status_filter)

    if client_type:
        query = query.where(Client.client_type == client_type)

    if locality_id:
        from app.models.locality import Locality
        loc_result = await db.execute(select(Locality).where(Locality.id == locality_id))
        loc = loc_result.scalar_one_or_none()
        if loc:
            query = query.where(
                or_(
                    Client.locality_id == locality_id,
                    Client.locality.ilike(f"%{loc.name}%")
                )
            )
        else:
            query = query.where(Client.locality_id == locality_id)

    if billing_group_id:
        query = query.where(Client.billing_group_id == billing_group_id)

    if has_balance == "yes":
        query = query.where(Client.balance != 0)
    elif has_balance == "no":
        query = query.where(Client.balance == 0)

    if broadcast_medium:
        query = query.where(Client.broadcast_medium.ilike(f"%{broadcast_medium}%"))

    if cut_day:
        query = query.where(Client.cut_day == cut_day)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * per_page
    query = query.order_by(Client.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    clients = result.scalars().all()

    return {
        "clients": [ClientResponse.model_validate(c) for c in clients],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene un cliente por ID."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    return ClientResponse.model_validate(client)


@router.post("/", response_model=ClientResponse, status_code=201)
async def create_client(
    data: ClientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea un nuevo cliente para el tenant."""
    tenant_id = current_user.tenant_id

    client = Client(
        tenant_id=tenant_id,
        **data.model_dump()
    )
    db.add(client)
    await db.flush()

    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza un cliente existente."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.flush()
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete de un cliente."""
    tenant_id = current_user.tenant_id

    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    client.is_active = False
    await db.flush()