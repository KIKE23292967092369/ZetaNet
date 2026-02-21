"""
Sistema ISP - Schemas: Células y OLT
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.cell import CellType, AddressAssignment


# --- Cell ---
class CellBase(BaseModel):
    name: str = Field(..., max_length=200)
    cell_type: CellType
    address: Optional[str] = None
    range_meters: Optional[int] = None
    assignment: AddressAssignment
    use_pcq: bool = False

    # PPPoE (solo FIBRA PPPoE)
    pppoe_service_ip: Optional[str] = None
    pppoe_password_encrypted: Optional[str] = None

    # DHCP Pool (FIBRA IPoE o ANTENAS DHCP)
    dhcp_pool_start: Optional[str] = None
    dhcp_pool_end: Optional[str] = None
    dhcp_gateway: Optional[str] = None
    dhcp_dns1: Optional[str] = None
    dhcp_dns2: Optional[str] = None
    dhcp_lease_time: Optional[str] = "1d"
    dhcp_interface: Optional[str] = None

    # Queues
    queue_total: Optional[str] = None
    queue_upload: Optional[str] = None
    queue_download: Optional[str] = None

    # Coordenadas
    latitude: Optional[str] = None
    longitude: Optional[str] = None

    # Config
    enable_usage_graphs: bool = False
    web_port: Optional[int] = None
    potential_connections: Optional[int] = None
    estimated_subscribers_pct: Optional[float] = None
    extra_data: Optional[str] = None

    # MikroTik
    mikrotik_host: Optional[str] = None
    mikrotik_username_encrypted: Optional[str] = None
    mikrotik_password_encrypted: Optional[str] = None
    mikrotik_api_port: int = 8728
    mikrotik_sftp_port: Optional[int] = None
    mikrotik_use_ssl: bool = False
    mikrotik_interface: Optional[str] = None

    # CPE creds (ANTENAS)
    cpe_username: Optional[str] = None
    cpe_password_encrypted: Optional[str] = None
    use_selected_ranges_only: bool = False

    # IPv4
    ipv4_range: Optional[str] = None
    ipv4_mask: Optional[str] = None
    ipv4_host_min: Optional[str] = None
    ipv4_host_max: Optional[str] = None
    ipv6_enabled: bool = False

    


class CellCreate(CellBase):
    plan_ids: Optional[List[int]] = []    # Planes a asignar


class CellUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    range_meters: Optional[int] = None
    use_pcq: Optional[bool] = None
    is_active: Optional[bool] = None

    # MikroTik
    mikrotik_host: Optional[str] = None
    mikrotik_api_port: Optional[int] = None
    mikrotik_use_ssl: Optional[bool] = None
    mikrotik_username_encrypted: Optional[str] = None
    mikrotik_password_encrypted: Optional[str] = None
    mikrotik_interface: Optional[str] = None
    

    # Queues
    queue_total: Optional[str] = None
    queue_upload: Optional[str] = None
    queue_download: Optional[str] = None

    # PPPoE
    pppoe_service_ip: Optional[str] = None
    pppoe_password_encrypted: Optional[str] = None

    # DHCP Pool
    dhcp_pool_start: Optional[str] = None
    dhcp_pool_end: Optional[str] = None
    dhcp_gateway: Optional[str] = None
    dhcp_dns1: Optional[str] = None
    dhcp_dns2: Optional[str] = None
    dhcp_lease_time: Optional[str] = None
    dhcp_interface: Optional[str] = None

    # IPv4
    ipv4_range: Optional[str] = None
    ipv4_mask: Optional[str] = None
    ipv4_host_min: Optional[str] = None
    ipv4_host_max: Optional[str] = None

    # Planes
    plan_ids: Optional[List[int]] = None

    class Config:
        from_attributes = True


class CellResponse(CellBase):
    id: int
    tenant_id: int
    is_active: bool
    is_initialized: bool
    has_connections: bool
    is_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CellListResponse(BaseModel):
    id: int
    name: str
    cell_type: CellType
    network_mode: Optional[str]
    assignment: AddressAssignment
    mikrotik_host: Optional[str]
    is_active: bool
    is_initialized: bool
    has_connections: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- OLT Config ---
class OltConfigBase(BaseModel):
    model_name: Optional[str] = None
    brand: Optional[str] = None
    total_ports: Optional[int] = None
    traffic_control: str = "Router Mikrotik"
    olt_ip: Optional[str] = None
    attenuation_tolerance: Optional[str] = None
    ssh_port: int = 22
    ssh_username_encrypted: Optional[str] = None
    ssh_password_encrypted: Optional[str] = None
    snmp_port: int = 161
    snmp_community_read: Optional[str] = None
    snmp_community_write: Optional[str] = None
    onu_port: Optional[int] = None
    onu_username_encrypted: Optional[str] = None
    onu_password_encrypted: Optional[str] = None


class OltConfigCreate(OltConfigBase):
    cell_id: Optional[int] = None 


class OltConfigResponse(OltConfigBase):
    id: int
    cell_id: int
    is_active: bool
    is_online: bool
    created_at: datetime

    class Config:
        from_attributes = True