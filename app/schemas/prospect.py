"""
Sistema ISP - Schemas: Prospectos
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.prospect import ProspectStatus, InstallationType


class ProspectBase(BaseModel):
    first_name: str = Field(..., max_length=200)
    last_name: str = Field(..., max_length=200)
    phone: Optional[str] = None
    phone_alt: Optional[str] = None
    email: Optional[str] = None
    locality: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    installation_type: Optional[InstallationType] = None
    broadcast_medium: Optional[str] = None
    extra_data: Optional[str] = None


class ProspectCreate(ProspectBase):
    pass


class ProspectUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[ProspectStatus] = None
    installation_type: Optional[InstallationType] = None

    class Config:
        from_attributes = True


class ProspectResponse(ProspectBase):
    id: int
    tenant_id: int
    status: ProspectStatus
    converted_client_id: Optional[int]
    registered_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Follow Up ---
class FollowUpCreate(BaseModel):
    note: str


class FollowUpResponse(BaseModel):
    id: int
    prospect_id: int
    user_id: Optional[int]
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProspectDetailResponse(ProspectResponse):
    follow_ups: List[FollowUpResponse] = []
