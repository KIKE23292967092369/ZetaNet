"""
Sistema ISP - Modelos de jerarquía de red FIBRA
Zona OLT → NAP → Puerto NAP
Cada zona = colonia/sector. Cada NAP = caja de distribución. Cada puerto = hilo de fibra.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


class OltZone(TenantBase):
    """Zona OLT = colonia/sector donde llega la fibra."""
    __tablename__ = "olt_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_id = Column(Integer, ForeignKey("cells.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(200), nullable=False)                 # ej: "PASEO DE LA RIVERA"
    slot_port = Column(String(20), nullable=True)              # ej: "4/1" (slot/puerto en la OLT)

    is_active = Column(Boolean, default=True)

    # Relationships
    cell = relationship("Cell", back_populates="olt_zones")
    naps = relationship("Nap", back_populates="olt_zone", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OltZone {self.name} ({self.slot_port})>"


class Nap(TenantBase):
    """NAP = caja de distribución en la calle."""
    __tablename__ = "naps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    olt_zone_id = Column(Integer, ForeignKey("olt_zones.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(200), nullable=False)                 # ej: "NAP 1 PUERTO 1"
    description = Column(Text, nullable=True)
    address = Column(String(500), nullable=True)               # Dirección física
    total_ports = Column(Integer, nullable=False, default=16)  # Número de puertos (hilos)
    distance_meters = Column(Integer, nullable=True)
    reference_value = Column(String(100), nullable=True)       # Valor referencia

    # Coordenadas
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)

    # Foto
    photo_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)

    # Relationships
    olt_zone = relationship("OltZone", back_populates="naps")
    ports = relationship("NapPort", back_populates="nap", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NAP {self.name} ({self.total_ports} ports)>"


class NapPort(TenantBase):
    """Puerto de NAP = hilo de fibra individual."""
    __tablename__ = "nap_ports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nap_id = Column(Integer, ForeignKey("naps.id", ondelete="CASCADE"), nullable=False, index=True)

    port_number = Column(Integer, nullable=False)              # 1-16 por NAP
    is_occupied = Column(Boolean, default=False)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=True)  # Ocupado por esta conexión

    # Relationships
    nap = relationship("Nap", back_populates="ports")
    connection = relationship("Connection", foreign_keys=[connection_id])

    def __repr__(self):
        return f"<NapPort {self.port_number} ({'occupied' if self.is_occupied else 'free'})>"
