"""
Sistema ISP - Schemas: Inventario
MAC única por tenant validada a nivel app.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# --- Brand ---
class BrandCreate(BaseModel):
    name: str = Field(..., max_length=100)


class BrandResponse(BaseModel):
    id: int
    name: str
    is_active: bool

    class Config:
        from_attributes = True


# --- Device Model ---
class DeviceModelCreate(BaseModel):
    brand_id: int
    name: str = Field(..., max_length=200)
    device_type: str                              # "onu", "cpe", "router"


class DeviceModelResponse(BaseModel):
    id: int
    brand_id: int
    name: str
    device_type: str
    is_active: bool

    class Config:
        from_attributes = True


# --- Supplier ---
class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=200)
    locality: Optional[str] = None
    address: Optional[str] = None
    rfc: Optional[str] = None
    phone: Optional[str] = None


class SupplierResponse(BaseModel):
    id: int
    name: str
    balance: float
    locality: Optional[str]
    address: Optional[str]
    rfc: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- ONU ---
class OnuCreate(BaseModel):
    model_id: Optional[int] = None
    mac_address: str = Field(..., max_length=17)    # MAC del equipo (única)
    mac_optical_port: Optional[str] = None
    serial_number: str = Field(..., max_length=100)
    detail: Optional[str] = None
    access_default: bool = True
    port: Optional[str] = None
    username_encrypted: Optional[str] = None
    password_encrypted: Optional[str] = None


class OnuUpdate(BaseModel):
    detail: Optional[str] = None
    is_active: Optional[bool] = None
    port: Optional[str] = None

    class Config:
        from_attributes = True


class OnuResponse(BaseModel):
    id: int
    model_id: Optional[int]
    mac_address: str
    mac_optical_port: Optional[str]
    serial_number: str
    detail: Optional[str]
    is_active: bool
    connection_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class OnuListResponse(BaseModel):
    id: int
    mac_address: str
    serial_number: str
    model_name: str = ""
    brand_name: str = ""
    is_active: bool
    connection_id: Optional[int]
    client_name: str = ""

    class Config:
        from_attributes = True


# --- CPE ---
class CpeCreate(BaseModel):
    model_id: Optional[int] = None
    mac_ether1: str = Field(..., max_length=17)     # MAC principal (única)
    mac_wlan: Optional[str] = None                   # Auto desde Ether1
    access_default: bool = True
    username_encrypted: Optional[str] = None
    password_encrypted: Optional[str] = None


class CpeUpdate(BaseModel):
    is_active: Optional[bool] = None
    mac_wlan: Optional[str] = None

    class Config:
        from_attributes = True


class CpeResponse(BaseModel):
    id: int
    model_id: Optional[int]
    mac_ether1: str
    mac_wlan: Optional[str]
    is_active: bool
    connection_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class CpeListResponse(BaseModel):
    id: int
    mac_ether1: str
    mac_wlan: Optional[str]
    model_name: str = ""
    brand_name: str = ""
    is_active: bool
    connection_id: Optional[int]
    client_name: str = ""

    class Config:
        from_attributes = True


# --- Router ---
class RouterCreate(BaseModel):
    model_id: Optional[int] = None
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    username_encrypted: Optional[str] = None
    password_encrypted: Optional[str] = None


class RouterResponse(BaseModel):
    id: int
    model_id: Optional[int]
    mac_address: Optional[str]
    serial_number: Optional[str]
    is_active: bool
    connection_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
