"""
Sistema ISP - Schemas: Red (Zonas OLT, NAPs, Puertos)
Cascada: Célula → Zona OLT → NAP → Puerto
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# --- OLT Zone ---
class OltZoneCreate(BaseModel):
    cell_id: int
    name: str = Field(..., max_length=200)
    slot_port: Optional[str] = None


class OltZoneUpdate(BaseModel):
    name: Optional[str] = None
    slot_port: Optional[str] = None
    is_active: Optional[bool] = None


class OltZoneResponse(BaseModel):
    id: int
    cell_id: int
    name: str
    slot_port: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- NAP ---
class NapCreate(BaseModel):
    olt_zone_id: int
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    address: Optional[str] = None
    total_ports: int = Field(default=16, ge=1, le=128)
    distance_meters: Optional[int] = None
    reference_value: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class NapUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    total_ports: Optional[int] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    is_active: Optional[bool] = None


class NapPortResponse(BaseModel):
    id: int
    port_number: int
    is_occupied: bool
    connection_id: Optional[int]

    class Config:
        from_attributes = True


class NapResponse(BaseModel):
    id: int
    olt_zone_id: int
    name: str
    description: Optional[str]
    address: Optional[str]
    total_ports: int
    distance_meters: Optional[int]
    latitude: Optional[str]
    longitude: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NapDetailResponse(NapResponse):
    ports: List[NapPortResponse] = []
    occupied_count: int = 0
    free_count: int = 0


# --- Cascade responses (para dropdowns de conexión) ---
class CascadeZoneResponse(BaseModel):
    """Para dropdown de Zonas OLT al crear conexión."""
    id: int
    name: str
    slot_port: Optional[str]
    nap_count: int = 0

    class Config:
        from_attributes = True


class CascadeNapResponse(BaseModel):
    """Para dropdown de NAPs al crear conexión."""
    id: int
    name: str
    total_ports: int
    free_ports: int = 0

    class Config:
        from_attributes = True


class CascadeFreePortResponse(BaseModel):
    """Para dropdown de puertos libres al crear conexión."""
    id: int
    port_number: int

    class Config:
        from_attributes = True
