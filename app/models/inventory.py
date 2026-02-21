"""
Sistema ISP - Modelos de Inventario
ONUs (fibra), CPEs (antenas), Routers, Proveedores, Marcas, Modelos.
MAC única en todo el sistema (validación a nivel app).
Al crear conexión, solo aparecen equipos con estatus Activo y SIN conexión.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Numeric, Date,
    ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


# ===== CATÁLOGOS =====

class Brand(TenantBase):
    """Marcas de equipos: Ubiquiti, Cambium, Huawei, ZTE, etc."""
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    models = relationship("DeviceModel", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Brand {self.name}>"


class DeviceModel(TenantBase):
    """Modelos de equipos: FORCE 130, HG8145 V5, ZXHN F670L, etc."""
    __tablename__ = "device_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)                 # ej: "FORCE 130"
    device_type = Column(String(20), nullable=False)           # "onu", "cpe", "router"
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    brand = relationship("Brand", back_populates="models")

    @property
    def full_name(self):
        return f"{self.brand.name} ({self.name})" if self.brand else self.name

    def __repr__(self):
        return f"<Model {self.name} ({self.device_type})>"


# ===== PROVEEDORES =====

class Supplier(TenantBase):
    """Proveedores de equipos."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    balance = Column(Numeric(12, 2), default=0)                # Saldo $
    locality = Column(String(300), nullable=True)
    address = Column(String(500), nullable=True)
    rfc = Column(String(13), nullable=True)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="suppliers")
    receptions = relationship("MerchandiseReception", back_populates="supplier", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Supplier {self.name}>"


class MerchandiseReception(TenantBase):
    """Recepción de mercancía desde proveedor."""
    __tablename__ = "merchandise_receptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)

    # Recepción
    detail = Column(Text, nullable=True)
    warehouse = Column(String(200), nullable=True)             # Almacén
    reception_date = Column(Date, nullable=True)
    extra_data = Column(Text, nullable=True)

    # Factura
    invoice_series_folio = Column(String(100), nullable=True)  # Serie + Folio
    invoice_date = Column(Date, nullable=True)
    invoice_detail = Column(String(200), nullable=True)        # ej: "Migración"
    subtotal = Column(Numeric(12, 2), default=0)               # Importe
    iva = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)

    # Relationships
    supplier = relationship("Supplier", back_populates="receptions")

    def __repr__(self):
        return f"<Reception {self.invoice_series_folio}>"


# ===== EQUIPOS =====

class Onu(TenantBase):
    """ONUs para fibra óptica. MAC única en todo el tenant."""
    __tablename__ = "onus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("device_models.id"), nullable=True)
    reception_id = Column(Integer, ForeignKey("merchandise_receptions.id"), nullable=True)

    mac_address = Column(String(17), nullable=False, index=True)   # MAC del equipo (única)
    mac_optical_port = Column(String(17), nullable=True)           # MAC puerto óptico
    serial_number = Column(String(100), nullable=False)            # Número de Serie
    detail = Column(Text, nullable=True)                           # ej: "Le falta la tapa trasera"
    image_url = Column(String(500), nullable=True)

    # Acceso
    access_default = Column(Boolean, default=True)                 # Checkbox Acceso Default
    port = Column(String(20), nullable=True)
    username_encrypted = Column(Text, nullable=True)
    password_encrypted = Column(Text, nullable=True)

    # Estado
    is_active = Column(Boolean, default=True)
    connection_id = Column(Integer, nullable=True)                 # Se llena al asignar (no FK para evitar circular)

    # Relationships
    tenant = relationship("Tenant", back_populates="onus")
    model = relationship("DeviceModel", foreign_keys=[model_id])
    reception = relationship("MerchandiseReception", foreign_keys=[reception_id])

    def __repr__(self):
        return f"<ONU {self.serial_number} ({self.mac_address})>"


class Cpe(TenantBase):
    """CPEs para antenas (Ubiquiti, Cambium). MAC única en todo el tenant."""
    __tablename__ = "cpes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("device_models.id"), nullable=True)
    reception_id = Column(Integer, ForeignKey("merchandise_receptions.id"), nullable=True)

    mac_ether1 = Column(String(17), nullable=False, index=True)    # MAC Ether1 (principal, única)
    mac_wlan = Column(String(17), nullable=True)                   # MAC WLAN (auto desde Ether1)
    image_url = Column(String(500), nullable=True)

    # Acceso
    access_default = Column(Boolean, default=True)
    username_encrypted = Column(Text, nullable=True)
    password_encrypted = Column(Text, nullable=True)

    # Estado
    is_active = Column(Boolean, default=True)
    connection_id = Column(Integer, nullable=True)                 # Se llena al asignar

    # Relationships
    tenant = relationship("Tenant", back_populates="cpes")
    model = relationship("DeviceModel", foreign_keys=[model_id])
    reception = relationship("MerchandiseReception", foreign_keys=[reception_id])

    def __repr__(self):
        return f"<CPE {self.mac_ether1}>"


class Router(TenantBase):
    """Routers del inventario (opcionales en conexiones ANTENA)."""
    __tablename__ = "routers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("device_models.id"), nullable=True)
    reception_id = Column(Integer, ForeignKey("merchandise_receptions.id"), nullable=True)

    mac_address = Column(String(17), nullable=True, index=True)
    serial_number = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)

    # Acceso
    username_encrypted = Column(Text, nullable=True)
    password_encrypted = Column(Text, nullable=True)

    # Estado
    is_active = Column(Boolean, default=True)
    connection_id = Column(Integer, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="routers")
    model = relationship("DeviceModel", foreign_keys=[model_id])
    reception = relationship("MerchandiseReception", foreign_keys=[reception_id])

    def __repr__(self):
        return f"<Router {self.serial_number}>"
