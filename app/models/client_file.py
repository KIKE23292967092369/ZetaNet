"""
Sistema ISP - Modelo: Archivos de Cliente
"""
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base


class FileCategory(str, enum.Enum):
    INE = "ine"
    CONTRATO = "contrato"
    COMPROBANTE = "comprobante"
    FOTO_INSTALACION = "foto_instalacion"
    FOTO_EQUIPO = "foto_equipo"
    OTRO = "otro"


class ClientFile(Base):
    __tablename__ = "client_files"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    file_name = Column(String(255), nullable=False)        # nombre original del archivo
    stored_name = Column(String(255), nullable=False)       # nombre en disco (con UUID)
    file_path = Column(String(500), nullable=False)         # ruta completa en disco
    file_type = Column(String(100), nullable=False)         # MIME type: image/jpeg, application/pdf
    file_size = Column(Integer, nullable=False)             # tamaño en bytes
    category = Column(Enum(FileCategory), nullable=False, default=FileCategory.OTRO)
    description = Column(String(255), nullable=True)        # nota opcional

    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    client = relationship("Client", backref="files")
    uploader = relationship("User", backref="uploaded_files")