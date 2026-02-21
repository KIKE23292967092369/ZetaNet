"""
Sistema ISP - Modelo OltConfig
Configuración de OLT por célula FIBRA.
Conexión SSH/SNMP para monitoreo y autorización de ONUs.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


class OltConfig(TenantBase):
    __tablename__ = "olt_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_id = Column(Integer, ForeignKey("cells.id", ondelete="CASCADE"), nullable=False, unique=True)

    # --- Modelo ---
    model_name = Column(String(200), nullable=True)
    brand = Column(String(100), nullable=True)
    total_ports = Column(Integer, nullable=True)
    traffic_control = Column(String(100), default="Router Mikrotik")

    # --- Conexión principal ---
    olt_ip = Column(String(255), nullable=True)
    attenuation_tolerance = Column(String(50), nullable=True)

    # --- SSH ---
    ssh_port = Column(Integer, default=22)
    ssh_username_encrypted = Column(Text, nullable=True)
    ssh_password_encrypted = Column(Text, nullable=True)

    # --- SNMP ---
    snmp_port = Column(Integer, default=161)
    snmp_community_read = Column(String(100), nullable=True)
    snmp_community_write = Column(String(100), nullable=True)

    # --- Conexión ONU (acceso remoto a ONUs) ---
    onu_port = Column(Integer, nullable=True)
    onu_username_encrypted = Column(Text, nullable=True)
    onu_password_encrypted = Column(Text, nullable=True)

    # --- Estado ---
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)

    # --- Autorización de ONUs ---
    auth_mode = Column(String(20), default="manual")
    default_line_profile = Column(String(100), nullable=True)
    default_service_profile = Column(String(100), nullable=True)
    default_vlan = Column(String(20), default="100")
    default_onu_type = Column(String(100), nullable=True)

    # --- Relationships ---
    cell = relationship("Cell", back_populates="olt_config")
    olt_profiles = relationship("OltProfile", back_populates="olt_config", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OLT {self.brand} {self.model_name} @ {self.olt_ip}>"