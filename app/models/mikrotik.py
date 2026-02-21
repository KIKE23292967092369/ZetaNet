"""
NetKeeper - Modelo TenantMikrotik
Cada ISP registra sus routers MikroTik.
Credenciales encriptadas con AES-256.
"""
from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


class TenantMikrotik(TenantBase):
    __tablename__ = "tenant_mikrotiks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)           # "Router Principal", "Nodo Sur"
    host = Column(String(255), nullable=False)            # IP o hostname
    port = Column(Integer, default=8728)                  # API port (8728) o API-SSL (8729)
    username_encrypted = Column(Text, nullable=False)     # Encriptado AES-256-GCM
    password_encrypted = Column(Text, nullable=False)     # Encriptado AES-256-GCM
    use_ssl = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="mikrotiks")

    def __repr__(self):
        return f"<MikroTik {self.name} @ {self.host}>"
