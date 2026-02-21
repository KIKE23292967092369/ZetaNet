"""
Sistema ISP - Modelos del Módulo Financiero (Paso 4)
Grupos de corte, facturas, pagos, configuración tapipay.

Recargo:
  - CON_PLAN: Si no paga el día de corte, al día siguiente se genera
    factura extra de $50 (configurable en billing_group.reconnection_fee)
  - PREPAGO: No se cobra recargo, puede pagar cuando quiera
  - Ambos se suspenden si no pagan después de los días de gracia
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Float,
    ForeignKey, Date, DateTime, Enum, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import TenantBase


# ================================================================
# ENUMS
# ================================================================

class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class InvoiceType(str, enum.Enum):
    MONTHLY = "monthly"               # Factura mensual de servicio
    LATE_FEE = "late_fee"             # Recargo por no pagar a tiempo ($50)
    MANUAL = "manual"                 # Factura creada manualmente
    OTHER = "other"


class PaymentMethod(str, enum.Enum):
    CARD = "card"
    CASH = "cash"
    TRANSFER = "transfer"
    MANUAL = "manual"
    OTHER = "other"


class PaymentStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERSED = "reversed"
    PENDING = "pending"


# ================================================================
# GRUPO DE CORTE (BILLING GROUP)
# ================================================================

class BillingGroup(TenantBase):
    __tablename__ = "billing_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(100), nullable=False)
    cutoff_day = Column(Integer, nullable=False)          # 1-28
    grace_days = Column(Integer, default=5)               # Días de gracia antes de suspender
    reconnection_fee = Column(Float, default=50.0)        # Recargo por pago tardío (solo CON_PLAN)
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)

    # Relationships
    clients = relationship("Client", back_populates="billing_group")
    invoices = relationship("Invoice", back_populates="billing_group")

    def __repr__(self):
        return f"<BillingGroup {self.name} (día {self.cutoff_day})>"


# ================================================================
# CONFIGURACIÓN TAPIPAY (POR TENANT)
# ================================================================

class TapipayConfig(TenantBase):
    __tablename__ = "tapipay_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    api_key = Column(String(500), nullable=False)
    username = Column(String(200), nullable=False)
    password = Column(String(500), nullable=False)

    company_code = Column(String(50), nullable=False)
    company_slug = Column(String(100), nullable=False)

    modality_id_digital = Column(String(100), nullable=True)
    modality_id_cash = Column(String(100), nullable=True)
    identifier_name_digital = Column(String(100), nullable=True)
    identifier_name_cash = Column(String(100), nullable=True)

    environment = Column(String(20), default="homo")
    webhook_secret = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)

    def get_payment_link(self, identifier_value: str) -> str:
        return f"https://www.tapipay.la/s/{self.company_slug}/portal/{identifier_value}/debts"


# ================================================================
# FACTURA (INVOICE)
# ================================================================

class Invoice(TenantBase):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relaciones
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=True, index=True)
    billing_group_id = Column(Integer, ForeignKey("billing_groups.id"), nullable=True)

    # Tipo de factura (mensual, recargo, manual)
    invoice_type = Column(Enum(InvoiceType), default=InvoiceType.MONTHLY)

    # Periodo
    period_month = Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    period_label = Column(String(50), nullable=True)

    # Montos
    amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    currency = Column(String(5), default="MXN")

    # Estado
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, index=True)
    due_date = Column(Date, nullable=False)
    suspension_date = Column(Date, nullable=True)

    # Datos tapipay
    tapipay_external_request_id = Column(String(100), nullable=True, unique=True)
    tapipay_tx = Column(String(100), nullable=True)
    tapipay_main_tx = Column(String(100), nullable=True)
    tapipay_reference_value = Column(String(200), nullable=True)
    tapipay_reference_image_url = Column(String(500), nullable=True)
    payment_link = Column(String(500), nullable=True)

    # Control
    tapipay_synced = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    client = relationship("Client", back_populates="invoices")
    connection = relationship("Connection", backref="invoices")
    billing_group = relationship("BillingGroup", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    @property
    def balance(self):
        return max(0, self.amount - (self.amount_paid or 0))

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.amount


# ================================================================
# PAGO (PAYMENT)
# ================================================================

class Payment(TenantBase):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.OTHER)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.CONFIRMED)

    tapipay_operation_id = Column(String(100), nullable=True)
    tapipay_external_payment_id = Column(String(100), nullable=True)
    tapipay_company_code = Column(String(50), nullable=True)
    tapipay_type = Column(String(50), nullable=True)
    tapipay_additional_data = Column(JSON, nullable=True)

    paid_at = Column(DateTime, default=datetime.utcnow)

    is_manual = Column(Boolean, default=False)
    registered_by = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    client = relationship("Client", backref="payments")