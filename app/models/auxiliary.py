"""
Sistema ISP - Modelos auxiliares
OltProfile: Line profiles y Remote profiles de la OLT.
ClientTag: Tags asignadas a clientes.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase
import enum


class ProfileType(str, enum.Enum):
    LINE = "line"
    REMOTE = "remote"


class OltProfile(TenantBase):
    """Line profiles y Remote profiles de la OLT. Se sincronizan vía SSH."""
    __tablename__ = "olt_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    olt_config_id = Column(Integer, ForeignKey("olt_configs.id", ondelete="CASCADE"), nullable=False, index=True)

    profile_type = Column(Enum(ProfileType), nullable=False)   # LINE o REMOTE
    name = Column(String(200), nullable=False)                 # ej: "lineprofile", "serviceprofile"
    t_cont = Column(String(100), nullable=True)                # T-CONT (solo LINE)
    upload_profile = Column(String(100), nullable=True)        # Perfil de subida
    download_profile = Column(String(100), nullable=True)      # Perfil de descarga
    has_traffic_profile = Column(Boolean, default=False)       # Asignar perfil de tráfico

    is_active = Column(Boolean, default=True)

    # Relationships
    olt_config = relationship("OltConfig", back_populates="olt_profiles")

    def __repr__(self):
        return f"<OltProfile {self.profile_type.value}: {self.name}>"


class ClientTag(TenantBase):
    """Tags asignadas a clientes para filtrar/clasificar."""
    __tablename__ = "client_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_name = Column(String(100), nullable=False)

    # Relationships
    client = relationship("Client", back_populates="tags")

    def __repr__(self):
        return f"<ClientTag {self.tag_name}>"
