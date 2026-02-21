"""
Sistema ISP - Schemas: Payment Gateways
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.payment_gateway import GatewayType


class GatewayConfigCreate(BaseModel):
    gateway_type: GatewayType
    api_key: str = Field(..., min_length=1)
    secret_key: Optional[str] = None
    merchant_id: Optional[str] = None
    webhook_secret: Optional[str] = None
    display_name: Optional[str] = None
    currency: str = "MXN"
    environment: str = "sandbox"          # sandbox / production


class GatewayConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    merchant_id: Optional[str] = None
    webhook_secret: Optional[str] = None
    display_name: Optional[str] = None
    currency: Optional[str] = None
    environment: Optional[str] = None
    is_active: Optional[bool] = None


class GatewayConfigResponse(BaseModel):
    id: int
    gateway_type: GatewayType
    display_name: Optional[str]
    currency: str
    environment: str
    is_active: bool
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateChargeRequest(BaseModel):
    """Crear un cobro genérico con la pasarela activa."""
    invoice_id: Optional[int] = None        # Vincular con factura
    client_id: int
    amount: float = Field(..., gt=0)
    description: str = "Pago de servicio de internet"
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class ChargeResponse(BaseModel):
    gateway: str
    charge_id: str
    payment_url: Optional[str] = None       # Link de pago para el cliente
    status: str
    amount: float
    currency: str
    reference: Optional[str] = None         # Referencia OXXO/SPEI
    barcode_url: Optional[str] = None       # Código de barras OXXO
    expires_at: Optional[str] = None