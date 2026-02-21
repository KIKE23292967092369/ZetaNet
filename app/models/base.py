"""
NetKeeper - Modelo base multi-tenant
Todos los modelos que pertenecen a un tenant heredan de TenantBase.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import declared_attr
from app.database import Base


class TimestampMixin:
    """Agrega created_at y updated_at a cualquier modelo."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TenantBase(Base, TimestampMixin):
    """
    Clase base para todas las tablas que pertenecen a un tenant.
    Automáticamente agrega tenant_id como FK.
    """
    __abstract__ = True

    @declared_attr
    def tenant_id(cls):
        return Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
