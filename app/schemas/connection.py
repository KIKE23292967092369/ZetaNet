"""
Sistema ISP - Schemas: Conexiones
Dos flujos: FIBRA (cascada completa) y ANTENA (directo).
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from app.models.connection import (
    ConnectionType, ConnectionStatus, BridgeRouterMode, CancelReason
)


# --- Crear conexión FIBRA ---
class ConnectionFiberCreate(BaseModel):
    client_id: int
    cell_id: int
    plan_id: int

    # Ubicación
    locality: Optional[str] = None
    address: Optional[str] = None
    street_between_1: Optional[str] = None
    street_between_2: Optional[str] = None
    extra_data: Optional[str] = None

    # Plan
    contract_date: Optional[date] = None
    is_free: bool = False

    # Cascada de red
    olt_zone_id: int
    nap_id: int
    nap_port_id: int
    ip_address: str                                # IP del rango PPPoE

    # PPPoE
    pppoe_profile: str = "default-encryption"
    pppoe_username: str
    pppoe_password_encrypted: str

    # ONU
    onu_id: int
    mode: BridgeRouterMode = BridgeRouterMode.ROUTER

    # Config avanzada
    api_credentials_source: Optional[str] = None
    ipv4_mark_output: str = "default_main"
    custom_priority: bool = False
    signal_dbm: Optional[float] = None

    # Coordenadas
    latitude: Optional[str] = None
    longitude: Optional[str] = None


# --- Crear conexión ANTENA ---
class ConnectionAntennaCreate(BaseModel):
    client_id: int
    cell_id: int
    plan_id: int

    # Ubicación
    locality: Optional[str] = None
    address: Optional[str] = None
    street_between_1: Optional[str] = None
    street_between_2: Optional[str] = None
    extra_data: Optional[str] = None

    # Plan
    contract_date: Optional[date] = None
    is_free: bool = False
    generate_month_charge: bool = True

    # Red (sin cascada)
    ip_address: str
    ip_additional: Optional[str] = None
    cpe_id: int
    router_id: Optional[int] = None
    is_backbone_router: bool = False

    # Config avanzada
    api_credentials_source: Optional[str] = None
    ipv4_mark_output: str = "default_main"
    custom_priority: bool = False

    # Coordenadas
    latitude: Optional[str] = None
    longitude: Optional[str] = None


# --- Autorizar ONU (FIBRA) ---
class AuthorizeOnuRequest(BaseModel):
    connection_id: int
    frame_slot_port: str                           # ej: "1/4/4"
    serial_number: str
    family: str                                    # ej: "ZTEG-F668"
    line_profile: str                              # ej: "lineprofile"
    remote_profile: str                            # ej: "serviceprofile"
    vlan: str                                      # ej: "100"


# --- Update ---
class ConnectionUpdate(BaseModel):
    status: Optional[ConnectionStatus] = None
    ip_address: Optional[str] = None
    plan_id: Optional[int] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# --- Cancelar conexión ---
class ConnectionCancelRequest(BaseModel):
    cancel_reason: CancelReason
    cancel_detail: Optional[str] = None


# --- Responses ---
class ConnectionResponse(BaseModel):
    id: int
    tenant_id: int
    client_id: int
    cell_id: int
    plan_id: Optional[int]
    connection_type: ConnectionType
    status: ConnectionStatus

    # Ubicación
    locality: Optional[str]
    address: Optional[str]

    # IP
    ip_address: Optional[str]
    latency_ms: Optional[float]

    # FIBRA
    olt_zone_id: Optional[int]
    nap_id: Optional[int]
    nap_port_id: Optional[int]
    pppoe_username: Optional[str]
    onu_id: Optional[int]
    mode: Optional[BridgeRouterMode]
    onu_authorized: bool = False

    # ANTENA
    cpe_id: Optional[int]
    router_id: Optional[int]

    # Coordenadas
    latitude: Optional[str]
    longitude: Optional[str]

    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionListResponse(BaseModel):
    id: int
    client_id: int
    client_name: str = ""
    connection_type: ConnectionType
    status: ConnectionStatus
    ip_address: Optional[str]
    plan_name: str = ""
    cell_name: str = ""
    created_at: datetime

    class Config:
        from_attributes = True
