"""
Sistema ISP - Router: Tickets
Tareas internas del ISP: instalación, eventos, cobranza, etc.
CRUD + notas de seguimiento + asignación + cierre.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timezone

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.client import Client
from app.models.ticket import Ticket, TicketNote, TicketStatus, TicketType, TicketPriority
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, TicketAssign,
    TicketResponse, TicketDetailResponse, TicketListResponse,
    TicketNoteCreate, TicketNoteResponse
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ════════════════════════════════════════════════════════
# CREAR TICKET
# ════════════════════════════════════════════════════════

@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Crear un ticket (tarea interna).
    Tipos: instalación, evento, cobranza, otro.
    Se puede vincular a un prospecto, cliente o conexión.
    """
    ticket = Ticket(
        tenant_id=user.tenant_id,
        ticket_type=data.ticket_type,
        priority=data.priority,
        subject=data.subject,
        description=data.description,
        prospect_id=data.prospect_id,
        client_id=data.client_id,
        connection_id=data.connection_id,
        assigned_to=data.assigned_to,
        scheduled_date=data.scheduled_date,
        created_by=user.id,
        status=TicketStatus.ABIERTO,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


# ════════════════════════════════════════════════════════
# LISTAR TICKETS
# ════════════════════════════════════════════════════════

@router.get("/", response_model=List[TicketListResponse])
async def list_tickets(
    ticket_type: Optional[TicketType] = None,
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
    priority: Optional[TicketPriority] = None,
    assigned_to: Optional[int] = None,
    client_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Listar tickets con filtros opcionales.
    Filtros: tipo, estado, prioridad, técnico asignado, cliente.
    """
    query = (
        select(Ticket)
        .options(selectinload(Ticket.assignee), selectinload(Ticket.client))
        .where(Ticket.tenant_id == user.tenant_id, Ticket.is_active == True)
    )

    if ticket_type:
        query = query.where(Ticket.ticket_type == ticket_type)
    if status_filter:
        query = query.where(Ticket.status == status_filter)
    if priority:
        query = query.where(Ticket.priority == priority)
    if assigned_to:
        query = query.where(Ticket.assigned_to == assigned_to)
    if client_id:
        query = query.where(Ticket.client_id == client_id)

    query = query.order_by(Ticket.created_at.desc())

    result = await db.execute(query)
    tickets = result.scalars().all()

    return [
        TicketListResponse(
            id=t.id,
            ticket_type=t.ticket_type,
            status=t.status,
            priority=t.priority,
            subject=t.subject,
            assigned_to=t.assigned_to,
            assignee_name=f"{t.assignee.first_name} {t.assignee.last_name}" if t.assignee and hasattr(t.assignee, 'first_name') else (t.assignee.username if t.assignee else None),
            client_id=t.client_id,
            client_name=f"{t.client.first_name} {t.client.last_name}" if t.client else None,
            scheduled_date=t.scheduled_date,
            created_at=t.created_at,
        )
        for t in tickets
    ]


# ════════════════════════════════════════════════════════
# VER TICKET (con notas)
# ════════════════════════════════════════════════════════

@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Ver un ticket con todo su historial de notas."""
    result = await db.execute(
        select(Ticket)
        .options(
            selectinload(Ticket.notes).selectinload(TicketNote.author),
            selectinload(Ticket.assignee),
            selectinload(Ticket.creator),
            selectinload(Ticket.client),
        )
        .where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket no encontrado")

    return TicketDetailResponse(
        id=ticket.id,
        tenant_id=ticket.tenant_id,
        ticket_type=ticket.ticket_type,
        status=ticket.status,
        priority=ticket.priority,
        subject=ticket.subject,
        description=ticket.description,
        prospect_id=ticket.prospect_id,
        client_id=ticket.client_id,
        connection_id=ticket.connection_id,
        assigned_to=ticket.assigned_to,
        created_by=ticket.created_by,
        scheduled_date=ticket.scheduled_date,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        is_active=ticket.is_active,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        assignee_name=ticket.assignee.username if ticket.assignee else None,
        creator_name=ticket.creator.username if ticket.creator else None,
        client_name=f"{ticket.client.first_name} {ticket.client.last_name}" if ticket.client else None,
        notes=[
            TicketNoteResponse(
                id=n.id,
                note=n.note,
                created_by=n.created_by,
                author_name=n.author.username if n.author else None,
                created_at=n.created_at,
            )
            for n in ticket.notes
        ]
    )


# ════════════════════════════════════════════════════════
# ACTUALIZAR TICKET
# ════════════════════════════════════════════════════════

@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Actualizar datos del ticket (asunto, prioridad, estado, asignación, etc.)."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == user.tenant_id
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket no encontrado")

    update_data = data.model_dump(exclude_unset=True)

    # Si cambia a resuelto, registrar fecha
    if update_data.get("status") == TicketStatus.RESUELTO and not ticket.resolved_at:
        update_data["resolved_at"] = datetime.now(timezone.utc)

    # Si cambia a cerrado, registrar fecha
    if update_data.get("status") == TicketStatus.CERRADO and not ticket.closed_at:
        update_data["closed_at"] = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(ticket, field, value)

    await db.commit()
    await db.refresh(ticket)
    return ticket


# ════════════════════════════════════════════════════════
# ASIGNAR TÉCNICO
# ════════════════════════════════════════════════════════

@router.post("/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: int,
    data: TicketAssign,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Asignar un técnico al ticket."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == user.tenant_id
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket no encontrado")

    # Verificar que el técnico existe y es del mismo tenant
    tech = await db.get(User, data.assigned_to)
    if not tech or tech.tenant_id != user.tenant_id:
        raise HTTPException(404, "Técnico no encontrado")

    ticket.assigned_to = data.assigned_to

    # Si estaba abierto, pasar a en_proceso
    if ticket.status == TicketStatus.ABIERTO:
        ticket.status = TicketStatus.EN_PROCESO

    # Agregar nota automática
    note = TicketNote(
        tenant_id=user.tenant_id,
        ticket_id=ticket.id,
        note=f"Ticket asignado a {tech.username}",
        created_by=user.id,
    )
    db.add(note)

    await db.commit()
    await db.refresh(ticket)
    return ticket


# ════════════════════════════════════════════════════════
# AGREGAR NOTA
# ════════════════════════════════════════════════════════

@router.post("/{ticket_id}/notes", response_model=TicketNoteResponse, status_code=status.HTTP_201_CREATED)
async def add_ticket_note(
    ticket_id: int,
    data: TicketNoteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Agregar una nota de seguimiento al ticket."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == user.tenant_id
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket no encontrado")

    if ticket.status in [TicketStatus.CERRADO, TicketStatus.CANCELADO]:
        raise HTTPException(400, "No se pueden agregar notas a un ticket cerrado o cancelado")

    note = TicketNote(
        tenant_id=user.tenant_id,
        ticket_id=ticket.id,
        note=data.note,
        created_by=user.id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return TicketNoteResponse(
        id=note.id,
        note=note.note,
        created_by=note.created_by,
        author_name=user.username,
        created_at=note.created_at,
    )


# ════════════════════════════════════════════════════════
# CERRAR TICKET
# ════════════════════════════════════════════════════════

@router.post("/{ticket_id}/close", response_model=TicketResponse)
async def close_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Cerrar un ticket. Registra fecha de cierre."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == user.tenant_id
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket no encontrado")

    if ticket.status == TicketStatus.CERRADO:
        raise HTTPException(400, "El ticket ya está cerrado")

    now = datetime.now(timezone.utc)

    # Si no fue marcado como resuelto antes, se resuelve al cerrar
    if not ticket.resolved_at:
        ticket.resolved_at = now

    ticket.status = TicketStatus.CERRADO
    ticket.closed_at = now

    # Nota automática
    note = TicketNote(
        tenant_id=user.tenant_id,
        ticket_id=ticket.id,
        note="Ticket cerrado",
        created_by=user.id,
    )
    db.add(note)

    await db.commit()
    await db.refresh(ticket)
    return ticket


# ════════════════════════════════════════════════════════
# CANCELAR TICKET
# ════════════════════════════════════════════════════════

@router.delete("/{ticket_id}", response_model=TicketResponse)
async def cancel_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Cancelar un ticket (soft delete)."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == user.tenant_id
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket no encontrado")

    ticket.status = TicketStatus.CANCELADO
    ticket.is_active = False

    # Nota automática
    note = TicketNote(
        tenant_id=user.tenant_id,
        ticket_id=ticket.id,
        note="Ticket cancelado",
        created_by=user.id,
    )
    db.add(note)

    await db.commit()
    await db.refresh(ticket)
    return ticket