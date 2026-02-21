"""
Sistema ISP - Modelo Client
Los suscriptores de internet de cada ISP.
Campos basados en formulario completo documentado en v1.3.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, Text, Numeric,
    Date, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase
import enum


class ClientType(str, enum.Enum):
    CON_PLAN = "con_plan"
    PREPAGO = "prepago"


class ClientStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PENDING = "pending"


class Client(TenantBase):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Datos personales (izquierda del formulario) ---
    contract_date = Column(Date, nullable=False)
    first_name = Column(String(200), nullable=False)
    last_name = Column(String(200), nullable=False)
    locality = Column(String(300), nullable=False)
    locality_id = Column(Integer, ForeignKey("localities.id"), nullable=True)  # NUEVO
    address = Column(String(500), nullable=False)
    zip_code = Column(String(10), nullable=True)
    official_id = Column(String(100), nullable=True)
    rfc = Column(String(13), nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referral = Column(String(200), nullable=True)
    requires_einvoice = Column(Boolean, default=False)

    # --- Contacto (derecha del formulario) ---
    phone_landline = Column(String(20), nullable=True)
    phone_cell = Column(String(20), nullable=True)
    phone_alt = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    email_alt = Column(String(255), nullable=True)
    broadcast_medium = Column(String(100), nullable=True)
    extra_data = Column(Text, nullable=True)

    # --- Facturación ---
    client_type = Column(Enum(ClientType), default=ClientType.CON_PLAN, nullable=False)
    billing_group_id = Column(Integer, ForeignKey("billing_groups.id"), nullable=True)
    cut_day = Column(Integer, nullable=True)  # Día de corte individual (1-31)
    no_suspend_first_month = Column(Boolean, default=True)
    apply_iva = Column(Boolean, default=False)
    bank_account = Column(String(50), nullable=True)

    # --- TapiPay (link de pago permanente) ---
    tapipay_identifier = Column(String(50), nullable=True, unique=True)   # "CLI-00045"
    payment_link = Column(String(500), nullable=True)                      # Link permanente

    # --- Estado ---
    status = Column(Enum(ClientStatus), default=ClientStatus.PENDING, nullable=False)
    balance = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    # --- Coordenadas ---
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)

    # --- Relationships ---
    tenant = relationship("Tenant", back_populates="clients")
    seller = relationship("User", foreign_keys=[seller_id])
    connections = relationship("Connection", back_populates="client", cascade="all, delete-orphan")
    tags = relationship("ClientTag", back_populates="client", cascade="all, delete-orphan")
    billing_group = relationship("BillingGroup", back_populates="clients")
    invoices = relationship("Invoice", back_populates="client")
    locality_rel = relationship("Locality", back_populates="clients", foreign_keys=[locality_id])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Client {self.full_name} ({self.status.value})>"