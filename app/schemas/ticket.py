"""
Sistema ISP - Schemas: Tickets
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from app.models.ticket import TicketType, TicketStatus, TicketPriority


# ── Ticket ─────────────────────────────────────────────

class TicketCreate(BaseModel):
    ticket_type: TicketType
    priority: TicketPriority = TicketPriority.MEDIA
    subject: str = Field(..., max_length=300)
    description: Optional[str] = None
    prospect_id: Optional[int] = None
    client_id: Optional[int] = None
    connection_id: Optional[int] = None
    assigned_to: Optional[int] = None
    scheduled_date: Optional[date] = None


class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    assigned_to: Optional[int] = None
    scheduled_date: Optional[date] = None
    client_id: Optional[int] = None
    connection_id: Optional[int] = None

    class Config:
        from_attributes = True


class TicketAssign(BaseModel):
    assigned_to: int


class TicketNoteResponse(BaseModel):
    id: int
    note: str
    created_by: int
    author_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    id: int
    tenant_id: int
    ticket_type: TicketType
    status: TicketStatus
    priority: TicketPriority
    subject: str
    description: Optional[str]
    prospect_id: Optional[int]
    client_id: Optional[int]
    connection_id: Optional[int]
    assigned_to: Optional[int]
    created_by: int
    scheduled_date: Optional[date]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketDetailResponse(TicketResponse):
    """Ticket con notas de seguimiento incluidas."""
    notes: List[TicketNoteResponse] = []
    assignee_name: Optional[str] = None
    creator_name: Optional[str] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    id: int
    ticket_type: TicketType
    status: TicketStatus
    priority: TicketPriority
    subject: str
    assigned_to: Optional[int]
    assignee_name: Optional[str] = None
    client_id: Optional[int]
    client_name: Optional[str] = None
    scheduled_date: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Nota ───────────────────────────────────────────────

class TicketNoteCreate(BaseModel):
    note: str = Field(..., min_length=1)