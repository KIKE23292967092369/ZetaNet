"""
Sistema ISP - Modelo Tenant (ISPs)
Cada ISP que se registra es un tenant.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin
import enum


class TenantPlan(str, enum.Enum):
    STARTER = "starter"          # $499 MXN/mes - hasta 100 clientes
    PROFESIONAL = "profesional"  # $999 MXN/mes - hasta 500 clientes
    ENTERPRISE = "enterprise"    # $1,999 MXN/mes - ilimitado


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    rfc = Column(String(13), nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)

    # Plan y estado
    plan = Column(Enum(TenantPlan), default=TenantPlan.STARTER, nullable=False)
    status = Column(Enum(TenantStatus), default=TenantStatus.TRIAL, nullable=False)
    max_clients = Column(Integer, default=100)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Configuración
    timezone = Column(String(50), default="America/Monterrey")
    currency = Column(String(3), default="MXN")
    is_active = Column(Boolean, default=True)

    # Credenciales servicios externos
    gupshup_api_key = Column(String(500), nullable=True)
    gupshup_app_name = Column(String(200), nullable=True)
    telegram_bot_token = Column(String(500), nullable=True)

    # --- Relationships ---
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    mikrotiks = relationship("TenantMikrotik", back_populates="tenant", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="tenant", cascade="all, delete-orphan")
    prospects = relationship("Prospect", back_populates="tenant", cascade="all, delete-orphan")
    cells = relationship("Cell", back_populates="tenant", cascade="all, delete-orphan")
    service_plans = relationship("ServicePlan", back_populates="tenant", cascade="all, delete-orphan")
    connections = relationship("Connection", back_populates="tenant", cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="tenant", cascade="all, delete-orphan")
    onus = relationship("Onu", back_populates="tenant", cascade="all, delete-orphan")
    cpes = relationship("Cpe", back_populates="tenant", cascade="all, delete-orphan")
    routers = relationship("Router", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.slug}: {self.name}>"
