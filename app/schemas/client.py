"""
Sistema ISP - Schemas: Clientes
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
from app.models.client import ClientType, ClientStatus


# --- Client ---
class ClientBase(BaseModel):
    contract_date: date
    first_name: str = Field(..., max_length=200)
    last_name: str = Field(..., max_length=200)
    locality: str = Field(..., max_length=300)
    address: str = Field(..., max_length=500)
    zip_code: Optional[str] = None
    official_id: Optional[str] = None
    rfc: Optional[str] = None
    seller_id: Optional[int] = None
    referral: Optional[str] = None
    requires_einvoice: bool = False

    # Contacto
    phone_landline: Optional[str] = None
    phone_cell: Optional[str] = None
    phone_alt: Optional[str] = None
    email: Optional[str] = None
    email_alt: Optional[str] = None
    broadcast_medium: Optional[str] = None
    extra_data: Optional[str] = None

    # Facturación
    client_type: ClientType = ClientType.CON_PLAN
    billing_group_id: Optional[int] = None
    cut_day: Optional[int] = None
    no_suspend_first_month: bool = True
    apply_iva: bool = False
    bank_account: Optional[str] = None

    # Coordenadas
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    locality_id: Optional[int] = None


class ClientUpdate(BaseModel):
    # Datos personales
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    locality: Optional[str] = None
    locality_id: Optional[int] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    official_id: Optional[str] = None
    rfc: Optional[str] = None
    seller_id: Optional[int] = None
    referral: Optional[str] = None
    requires_einvoice: Optional[bool] = None

    # Contacto
    phone_landline: Optional[str] = None
    phone_cell: Optional[str] = None
    phone_alt: Optional[str] = None
    email: Optional[str] = None
    email_alt: Optional[str] = None
    broadcast_medium: Optional[str] = None
    extra_data: Optional[str] = None

    # Facturación
    client_type: Optional[ClientType] = None
    billing_group_id: Optional[int] = None
    cut_day: Optional[int] = None
    no_suspend_first_month: Optional[bool] = None
    apply_iva: Optional[bool] = None
    bank_account: Optional[str] = None

    # Estado
    status: Optional[ClientStatus] = None
    balance: Optional[float] = None

    # Ubicación
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ClientResponse(ClientBase):
    id: int
    tenant_id: int
    locality_id: Optional[int] = None
    status: ClientStatus
    balance: float = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    id: int
    full_name: str
    status: ClientStatus
    balance: float
    client_type: ClientType
    locality: str
    address: str
    phone_cell: Optional[str]
    email: Optional[str]
    cut_day: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Client Tag ---
class ClientTagCreate(BaseModel):
    tag_name: str = Field(..., max_length=100)


class ClientTagResponse(BaseModel):
    id: int
    tag_name: str

    class Config:
        from_attributes = True