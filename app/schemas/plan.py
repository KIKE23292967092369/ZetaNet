"""
Sistema ISP - Schemas: Planes de Servicio
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.plan import PlanType


class ServicePlanBase(BaseModel):
    folio: Optional[str] = None
    name: str = Field(..., max_length=200)
    plan_type: PlanType = PlanType.CON_PLAN
    traffic_control: str = "Router Mikrotik"
    price: float = Field(..., gt=0)
    priority: str = "Residencial"
    reconnection_fee: bool = False
    restrict_by_tags: bool = False
    tags: Optional[str] = None

    # Velocidad
    upload_speed: str
    download_speed: str
    upload_unit: str = "MB"
    download_unit: str = "MB"

    # Burst
    burst_limit_upload: Optional[str] = None
    burst_limit_download: Optional[str] = None
    burst_threshold_upload: Optional[str] = None
    burst_threshold_download: Optional[str] = None
    burst_time_upload: Optional[str] = None
    burst_time_download: Optional[str] = None


class ServicePlanCreate(ServicePlanBase):
    cell_ids: Optional[List[int]] = []    # Células a asignar


class ServicePlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    upload_speed: Optional[str] = None
    download_speed: Optional[str] = None
    is_active: Optional[bool] = None
    cell_ids: Optional[List[int]] = None

    class Config:
        from_attributes = True


class ServicePlanResponse(ServicePlanBase):
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServicePlanListResponse(BaseModel):
    id: int
    name: str
    plan_type: PlanType
    price: float
    upload_speed: str
    download_speed: str
    priority: str
    tags: Optional[str]
    is_active: bool
    connection_count: int = 0
    cell_count: int = 0

    class Config:
        from_attributes = True


# --- Cell Interface (ANTENAS) ---
class CellInterfaceResponse(BaseModel):
    id: int
    cell_id: int
    interface_name: str
    ip_address: Optional[str]
    subnet: Optional[int]
    hosts: Optional[int]
    connections_allowed: bool

    class Config:
        from_attributes = True


class CellInterfaceUpdate(BaseModel):
    connections_allowed: bool
