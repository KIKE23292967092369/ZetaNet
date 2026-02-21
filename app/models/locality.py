"""
NetKeeper - Modelo Locality
Catálogo de localidades/colonias del ISP.
Los clientes se asignan a una localidad del catálogo.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


class Locality(TenantBase):
    __tablename__ = "localities"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Datos principales
    name = Column(String(300), nullable=False)          # Nombre de la localidad
    municipality = Column(String(200), nullable=False)   # Municipio
    state = Column(String(200), nullable=False)          # Entidad/Estado

    # Opcional
    zip_code = Column(String(10), nullable=True)         # Código postal
    clave_inegi = Column(String(20), nullable=True)      # Clave INEGI
    inhabited_homes = Column(Integer, nullable=True)     # Viviendas habitadas
    is_active = Column(Boolean, default=True)            # Para clientes (visible en dropdown)
    notes = Column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    clients = relationship("Client", back_populates="locality_rel", foreign_keys="Client.locality_id")

    def __repr__(self):
        return f"<Locality {self.name} ({self.municipality})>"