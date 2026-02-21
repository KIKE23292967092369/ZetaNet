"""
Sistema ISP - Modelo: Tickets
Tareas internas del ISP: instalación, eventos, cobranza, etc.
Con asignación a técnicos y seguimiento con notas.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, Date,
    ForeignKey, Enum, func
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


class TicketType(str, enum.Enum):
    INSTALACION = "instalacion"
    EVENTO = "evento"
    COBRANZA = "cobranza"
    OTRO = "otro"


class TicketStatus(str, enum.Enum):
    ABIERTO = "abierto"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"
    CANCELADO = "cancelado"


class TicketPriority(str, enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class Ticket(TenantBase):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Tipo, estado, prioridad ---
    ticket_type = Column(Enum(TicketType), nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.ABIERTO, nullable=False)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIA, nullable=False)

    # --- Detalle ---
    subject = Column(String(300), nullable=False)          # "Instalar fibra en calle 5"
    description = Column(Text, nullable=True)               # Detalle completo

    # --- Vinculación ---
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=True)   # Para instalación
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)       # Ya es cliente
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=True)  # Conexión afectada

    # --- Asignación ---
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)       # Técnico asignado
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)       # Quien creó el ticket

    # --- Fechas ---
    scheduled_date = Column(Date, nullable=True)            # Fecha programada (instalación/visita)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # --- Estado ---
    is_active = Column(Boolean, default=True)

    # --- Relationships ---
    tenant = relationship("Tenant")
    prospect = relationship("Prospect", backref="tickets")
    client = relationship("Client", backref="tickets")
    connection = relationship("Connection", backref="tickets")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_tickets")
    creator = relationship("User", foreign_keys=[created_by], backref="created_tickets")
    notes = relationship("TicketNote", back_populates="ticket", cascade="all, delete-orphan",
                         order_by="TicketNote.created_at.asc()")

    def __repr__(self):
        return f"<Ticket #{self.id} {self.ticket_type.value} ({self.status.value})>"


class TicketNote(TenantBase):
    __tablename__ = "ticket_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)

    # --- Contenido ---
    note = Column(Text, nullable=False)                     # "Se revisó ONU, señal ok"
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # --- Relationships ---
    ticket = relationship("Ticket", back_populates="notes")
    author = relationship("User", backref="ticket_notes")

    def __repr__(self):
        return f"<TicketNote #{self.id} ticket={self.ticket_id}>"