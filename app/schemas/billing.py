"""
Sistema ISP - Schemas del Módulo Financiero
Validación Pydantic para grupos de corte, facturas, pagos, tapipay.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


# ================================================================
# BILLING GROUP (GRUPO DE CORTE)
# ================================================================

class BillingGroupCreate(BaseModel):
    name: str = Field(..., max_length=100, examples=["Corte día 5"])
    cutoff_day: int = Field(..., ge=1, le=28, description="Día del mes (1-28)")
    grace_days: int = Field(default=5, ge=0, le=30, description="Días de gracia antes de suspender")
    reconnection_fee: float = Field(default=50.0, ge=0, description="Recargo por pago tardío (solo CON_PLAN)")
    description: Optional[str] = None

class BillingGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    cutoff_day: Optional[int] = Field(None, ge=1, le=28)
    grace_days: Optional[int] = Field(None, ge=0, le=30)
    reconnection_fee: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None

class BillingGroupResponse(BaseModel):
    id: int
    name: str
    cutoff_day: int
    grace_days: int
    reconnection_fee: float
    description: Optional[str] = None
    is_active: bool
    client_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ================================================================
# TAPIPAY CONFIG
# ================================================================

class TapipayConfigCreate(BaseModel):
    api_key: str
    username: str
    password: str
    company_code: str = Field(..., examples=["MX-S-00001"])
    company_slug: str = Field(..., examples=["mi-isp"])
    modality_id_digital: Optional[str] = None
    modality_id_cash: Optional[str] = None
    identifier_name_digital: Optional[str] = None
    identifier_name_cash: Optional[str] = None
    environment: str = Field(default="homo")
    webhook_secret: Optional[str] = None

class TapipayConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    company_code: Optional[str] = None
    company_slug: Optional[str] = None
    modality_id_digital: Optional[str] = None
    modality_id_cash: Optional[str] = None
    identifier_name_digital: Optional[str] = None
    identifier_name_cash: Optional[str] = None
    environment: Optional[str] = None
    webhook_secret: Optional[str] = None

class TapipayConfigResponse(BaseModel):
    id: int
    company_code: str
    company_slug: str
    environment: str
    modality_id_digital: Optional[str] = None
    modality_id_cash: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ================================================================
# INVOICE (FACTURA)
# ================================================================

class InvoiceCreate(BaseModel):
    client_id: int
    connection_id: Optional[int] = None
    amount: float = Field(..., gt=0)
    period_month: int = Field(..., ge=1, le=12)
    period_year: int = Field(..., ge=2024, le=2100)
    due_date: date
    notes: Optional[str] = None

class InvoiceResponse(BaseModel):
    id: int
    client_id: int
    connection_id: Optional[int] = None
    billing_group_id: Optional[int] = None
    invoice_type: str
    period_month: int
    period_year: int
    period_label: Optional[str] = None
    amount: float
    amount_paid: float
    currency: str
    status: str
    due_date: date
    suspension_date: Optional[date] = None
    payment_link: Optional[str] = None
    tapipay_synced: bool
    tapipay_reference_value: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerateBillingRequest(BaseModel):
    billing_group_id: int
    period_month: int = Field(..., ge=1, le=12)
    period_year: int = Field(..., ge=2024, le=2100)
    sync_tapipay: bool = Field(default=True)


class GenerateBillingResponse(BaseModel):
    billing_group: str
    period: str
    invoices_created: int
    invoices_synced_tapipay: int
    errors: List[str] = []


# ================================================================
# PAYMENT (PAGO)
# ================================================================

class PaymentManualCreate(BaseModel):
    invoice_id: int
    amount: float = Field(..., gt=0)
    payment_method: str = Field(default="manual")
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    client_id: int
    amount: float
    payment_method: str
    status: str
    tapipay_operation_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    is_manual: bool
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ================================================================
# TAPIPAY WEBHOOK
# ================================================================

class TapipayWebhookPayload(BaseModel):
    operationId: str
    status: str
    externalPaymentId: Optional[str] = None
    externalClientId: Optional[str] = None
    additionalData: Optional[dict] = None
    amount: float
    hash: Optional[str] = None
    type: Optional[str] = None
    createdAt: Optional[str] = None
    companyCode: Optional[str] = None
    companyName: Optional[str] = None


# ================================================================
# CLIENT BILLING INFO
# ================================================================

class ClientBillingInfo(BaseModel):
    client_id: int
    client_name: str
    tapipay_identifier: Optional[str] = None
    payment_link: Optional[str] = None
    billing_group: Optional[str] = None
    cutoff_day: Optional[int] = None
    pending_invoices: int = 0
    total_debt: float = 0.0
    last_payment_date: Optional[datetime] = None


# ================================================================
# ASSIGN CLIENT TO GROUP
# ================================================================

class AssignBillingGroupRequest(BaseModel):
    client_ids: List[int]
    billing_group_id: int


# ================================================================
# LATE FEE RESPONSE
# ================================================================

class LateFeeResponse(BaseModel):
    date: str
    late_fees_generated: int
    skipped_prepago: int
    errors: List[str] = []