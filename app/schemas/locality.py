"""
NetKeeper - Schemas: Localidades
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LocalityBase(BaseModel):
    name: str = Field(..., max_length=300)
    municipality: str = Field(..., max_length=200)
    state: str = Field(..., max_length=200)
    zip_code: Optional[str] = None
    clave_inegi: Optional[str] = None
    inhabited_homes: Optional[int] = None
    is_active: bool = True
    notes: Optional[str] = None


class LocalityCreate(LocalityBase):
    pass


class LocalityUpdate(BaseModel):
    name: Optional[str] = None
    municipality: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    clave_inegi: Optional[str] = None
    inhabited_homes: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class LocalityResponse(LocalityBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True