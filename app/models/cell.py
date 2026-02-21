"""
Sistema ISP - Modelo Cell (Célula)
Corazón del sistema. Define MikroTik, OLT, red, planes.
Sin célula configurada no se puede crear ninguna conexión.
Tipos: FIBRA (PPPoE), ANTENAS (IP Estática), HIFIBER_IPOE
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, Text, Numeric,
    ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase
import enum


class CellType(str, enum.Enum):
    FIBRA = "fibra"
    ANTENAS = "antenas"
    HIFIBER_IPOE = "hifiber_ipoe"


class AddressAssignment(str, enum.Enum):
    PPPOE_DISTRIBUTED = "pppoe_distributed"   # FIBRA PPPoE
    STATIC_ADDRESSING = "static_addressing"   # ANTENAS estático
    DHCP_POOL = "dhcp_pool"                   # FIBRA IPoE o ANTENAS DHCP


class Cell(TenantBase):
    __tablename__ = "cells"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Datos principales ---
    name = Column(String(200), nullable=False)
    cell_type = Column(Enum(CellType), nullable=False)
    network_mode = Column(String(20), default="pppoe")  # pppoe / dhcp / static
    address = Column(String(500), nullable=True)              # Dirección física
    range_meters = Column(Integer, nullable=True)              # 15000 (FIBRA) / 4000 (ANTENAS)
    assignment = Column(Enum(AddressAssignment), nullable=False)
    use_pcq = Column(Boolean, default=False)                   # Utilizar PCQ

    # --- PPPoE (solo FIBRA PPPoE) ---
    pppoe_service_ip = Column(String(45), nullable=True)       # IP del servicio PPPoE
    pppoe_password_encrypted = Column(Text, nullable=True)     # Contraseña PPPoE

    # --- DHCP Pool (FIBRA IPoE o ANTENAS DHCP) ---
    dhcp_pool_start = Column(String(45), nullable=True)        # ej: 192.168.10.100
    dhcp_pool_end = Column(String(45), nullable=True)          # ej: 192.168.10.200
    dhcp_gateway = Column(String(45), nullable=True)           # ej: 192.168.10.1
    dhcp_dns1 = Column(String(45), nullable=True)              # ej: 8.8.8.8
    dhcp_dns2 = Column(String(45), nullable=True)              # ej: 8.8.4.4
    dhcp_lease_time = Column(String(20), default="1d", nullable=True)  # ej: "1d", "12h"
    dhcp_interface = Column(String(100), nullable=True)        # interfaz MikroTik ej: "bridge1"

    # --- Estado ---
    is_active = Column(Boolean, default=True)
    is_initialized = Column(Boolean, default=False)
    has_connections = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)

    # --- Queues ---
    queue_total = Column(String(50), nullable=True)
    queue_upload = Column(String(50), nullable=True)
    queue_download = Column(String(50), nullable=True)

    # --- Coordenadas ---
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)

    # --- Configuración adicional ---
    enable_usage_graphs = Column(Boolean, default=False)       # Gráficas de consumo
    web_port = Column(Integer, nullable=True)
    potential_connections = Column(Integer, nullable=True)
    estimated_subscribers_pct = Column(Numeric(5, 2), nullable=True)
    extra_data = Column(Text, nullable=True)

    # --- Equipo MikroTik (cada célula tiene uno) ---
    mikrotik_host = Column(String(255), nullable=True)         # IP pública o dominio
    mikrotik_username_encrypted = Column(Text, nullable=True)
    mikrotik_password_encrypted = Column(Text, nullable=True)
    mikrotik_api_port = Column(Integer, default=8728)          # 8728 sin SSL / 8729 con SSL
    mikrotik_sftp_port = Column(Integer, nullable=True)
    mikrotik_use_ssl = Column(Boolean, default=False)          # Conexión API segura
    mikrotik_interface = Column(String(100), nullable=True)

    # --- Credenciales CPE (solo ANTENAS) ---
    cpe_username = Column(String(100), nullable=True)
    cpe_password_encrypted = Column(Text, nullable=True)
    use_selected_ranges_only = Column(Boolean, default=False)

    # --- IPv4 Config (ANTENAS estático / rangos generales) ---
    ipv4_range = Column(String(50), nullable=True)             # Rango IP ej: 192.168.10.0
    ipv4_mask = Column(String(10), nullable=True)              # Máscara ej: /24
    ipv4_host_min = Column(String(45), nullable=True)
    ipv4_host_max = Column(String(45), nullable=True)
    ipv6_enabled = Column(Boolean, default=False)

    

    # --- Relationships ---
    tenant = relationship("Tenant", back_populates="cells")
    olt_config = relationship("OltConfig", back_populates="cell", uselist=False, cascade="all, delete-orphan")
    olt_zones = relationship("OltZone", back_populates="cell", cascade="all, delete-orphan")
    cell_interfaces = relationship("CellInterface", back_populates="cell", cascade="all, delete-orphan")
    cell_plans = relationship("CellPlan", back_populates="cell", cascade="all, delete-orphan")
    connections = relationship("Connection", back_populates="cell", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cell {self.name} ({self.cell_type.value})>"