"""
Sistema ISP - Modelos de Planes de Servicio
Plan → se asigna a Células → clientes contratan.
Al crear un plan se configura automáticamente en el MikroTik.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, Text, Numeric,
    ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase
import enum


class PlanType(str, enum.Enum):
    CON_PLAN = "con_plan"       # Mensualidad fija
    PREPAGO = "prepago"          # Pago anticipado


class ServicePlan(TenantBase):
    __tablename__ = "service_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Datos principales ---
    folio = Column(String(50), nullable=True)
    name = Column(String(200), nullable=False)
    plan_type = Column(Enum(PlanType), default=PlanType.CON_PLAN, nullable=False)
    traffic_control = Column(String(100), default="Router Mikrotik")
    price = Column(Numeric(10, 2), nullable=False)             # Precio en MXN
    priority = Column(String(50), default="Residencial")       # Residencial, Empresarial...
    reconnection_fee = Column(Boolean, default=False)          # Cargo por reconexión
    restrict_by_tags = Column(Boolean, default=False)          # Restringir por tags
    tags = Column(String(200), nullable=True)                  # ej: "Solo UBIQUITI"

    # --- Velocidad (en MB o KB) ---
    upload_speed = Column(String(20), nullable=False)          # ej: "10M", "50M"
    download_speed = Column(String(20), nullable=False)
    upload_unit = Column(String(5), default="MB")              # MB / KB
    download_unit = Column(String(5), default="MB")

    # --- Burst (MikroTik) ---
    burst_limit_upload = Column(String(20), nullable=True)
    burst_limit_download = Column(String(20), nullable=True)
    burst_threshold_upload = Column(String(20), nullable=True)
    burst_threshold_download = Column(String(20), nullable=True)
    burst_time_upload = Column(String(10), nullable=True)      # Segundos
    burst_time_download = Column(String(10), nullable=True)

    # --- Estado ---
    is_active = Column(Boolean, default=True)

    # --- Relationships ---
    tenant = relationship("Tenant", back_populates="service_plans")
    cell_plans = relationship("CellPlan", back_populates="service_plan", cascade="all, delete-orphan")
    connections = relationship("Connection", back_populates="service_plan")

    def __repr__(self):
        return f"<Plan {self.name} ${self.price} ({self.plan_type.value})>"


class CellPlan(TenantBase):
    """Tabla pivote: qué planes están asignados a qué células."""
    __tablename__ = "cell_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_id = Column(Integer, ForeignKey("cells.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("service_plans.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    cell = relationship("Cell", back_populates="cell_plans")
    service_plan = relationship("ServicePlan", back_populates="cell_plans")

    def __repr__(self):
        return f"<CellPlan cell={self.cell_id} plan={self.plan_id}>"


class CellInterface(TenantBase):
    """
    Interfaces del MikroTik sincronizadas (solo ANTENAS).
    Checkbox 'Conexiones permitidas' define cuáles se usan para asignar IPs.
    """
    __tablename__ = "cell_interfaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_id = Column(Integer, ForeignKey("cells.id", ondelete="CASCADE"), nullable=False, index=True)

    interface_name = Column(String(100), nullable=False)       # ej: "ether3", "ether4"
    ip_address = Column(String(50), nullable=True)             # ej: "192.168.25.0/24"
    subnet = Column(Integer, nullable=True)                    # ej: 24
    hosts = Column(Integer, nullable=True)                     # ej: 254
    connections_allowed = Column(Boolean, default=False)        # Checkbox habilitada

    # Relationships
    cell = relationship("Cell", back_populates="cell_interfaces")

    def __repr__(self):
        return f"<Interface {self.interface_name} {'✓' if self.connections_allowed else '✗'}>"
