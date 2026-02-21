"""
Sistema ISP - Modelo: Payment Gateway Config
Configuración de pasarelas de pago por tenant.
Cada ISP elige qué pasarela usar (TapiPay, Conekta, Stripe, OpenPay, MercadoPago).
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime,
    ForeignKey, Enum, func
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


class GatewayType(str, enum.Enum):
    TAPIPAY = "tapipay"
    CONEKTA = "conekta"
    STRIPE = "stripe"
    OPENPAY = "openpay"
    MERCADOPAGO = "mercadopago"


class PaymentGatewayConfig(TenantBase):
    __tablename__ = "payment_gateway_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Tipo de pasarela ---
    gateway_type = Column(Enum(GatewayType), nullable=False)

    # --- Credenciales ---
    api_key = Column(Text, nullable=False)
    secret_key = Column(Text, nullable=True)              # Algunas requieren secret
    merchant_id = Column(String(200), nullable=True)       # OpenPay, MercadoPago
    webhook_secret = Column(String(200), nullable=True)    # Para verificar webhooks

    # --- Config adicional ---
    display_name = Column(String(200), nullable=True)      # "Pagos con Conekta"
    currency = Column(String(10), default="MXN")
    environment = Column(String(20), default="sandbox")    # sandbox / production

    # --- Estado ---
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)            # La que se usa por defecto

    # --- Relationships ---
    tenant = relationship("Tenant", backref="payment_gateways")

    def __repr__(self):
        return f"<PaymentGateway {self.gateway_type.value} ({'default' if self.is_default else 'secondary'})>"