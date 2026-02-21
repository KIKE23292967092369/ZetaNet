"""
Sistema ISP - Modelo Prospect
Pre-clientes que aún no contratan. Seguimiento hasta conversión.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase
import enum


class ProspectStatus(str, enum.Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    CONVERTED = "converted"       # Se convirtió en cliente
    REJECTED = "rejected"


class InstallationType(str, enum.Enum):
    FIBER = "fiber"
    ANTENNA = "antenna"


class Prospect(TenantBase):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Datos personales
    first_name = Column(String(200), nullable=False)
    last_name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=True)
    phone_alt = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)

    # Ubicación
    locality = Column(String(300), nullable=True)
    address = Column(String(500), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)

    # Clasificación
    installation_type = Column(Enum(InstallationType), nullable=True)
    status = Column(Enum(ProspectStatus), default=ProspectStatus.PENDING, nullable=False)
    broadcast_medium = Column(String(100), nullable=True)     # Medio de difusión
    extra_data = Column(Text, nullable=True)

    # Conversión
    converted_client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    registered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="prospects")
    converted_client = relationship("Client", foreign_keys=[converted_client_id])
    registered_by = relationship("User", foreign_keys=[registered_by_id])
    follow_ups = relationship("ProspectFollowUp", back_populates="prospect", cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Prospect {self.full_name} ({self.status.value})>"


class ProspectFollowUp(TenantBase):
    __tablename__ = "prospect_follow_ups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    note = Column(Text, nullable=False)

    # Relationships
    prospect = relationship("Prospect", back_populates="follow_ups")
    user = relationship("User")

    def __repr__(self):
        return f"<FollowUp prospect={self.prospect_id}>"
