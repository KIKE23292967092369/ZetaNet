"""
Sistema ISP - Schemas: Auth y Tenant
Schemas originales de autenticación y registro.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole
from app.models.tenant import TenantPlan, TenantStatus


# --- Auth ---
class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    tenant_id: int
    email: str
    username: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.AGENT


# --- Tenant ---
class TenantCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=100)
    email: str
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    email: str
    phone: Optional[str]
    plan: TenantPlan
    status: TenantStatus
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
