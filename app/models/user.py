"""
NetKeeper - Modelo User
Usuarios de cada ISP (admin, agente, técnico, facturación).
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from app.models.base import TenantBase
import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"   # Dueño de NetKeeper
    ADMIN = "admin"               # Dueño del ISP
    AGENT = "agent"               # Soporte
    TECHNICIAN = "technician"     # Técnico de campo
    BILLING = "billing"           # Facturación


class User(TenantBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.AGENT, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
