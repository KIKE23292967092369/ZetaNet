"""
Sistema ISP - Modelo Connection
Conexiones de internet. Dos tipos según célula:
  FIBRA: Célula → Zona OLT → NAP → Puerto → IP → PPPoE → ONU → Autorizar
  ANTENA: Célula → IP + MAC → CPE → Listo
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, Text, Numeric,
    Date, ForeignKey
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase
import enum


class ConnectionType(str, enum.Enum):
    FIBER = "fiber"
    ANTENNA = "antenna"


class ConnectionStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PENDING_INSTALL = "pending_install"
    PENDING_AUTH = "pending_auth"        # FIBRA: PPP creado, falta autorizar ONU


class BridgeRouterMode(str, enum.Enum):
    BRIDGE = "bridge"
    ROUTER = "router"


class CancelReason(str, enum.Enum):
    CLIENT_REQUEST = "client_request"    # Solicitud del cliente
    NON_PAYMENT = "non_payment"          # Falta de pago
    NO_LINE_OF_SIGHT = "no_line_sight"   # Sin línea de vista (antenas)
    OTHER = "other"


class Connection(TenantBase):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Relaciones principales ---
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    cell_id = Column(Integer, ForeignKey("cells.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("service_plans.id"), nullable=True)

    # --- Tipo y estado ---
    connection_type = Column(Enum(ConnectionType), nullable=False)
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.PENDING_INSTALL, nullable=False)

    # --- Datos ubicación ---
    locality = Column(String(300), nullable=True)
    address = Column(String(500), nullable=True)               # Domicilio
    street_between_1 = Column(String(200), nullable=True)      # Entre Calle 1
    street_between_2 = Column(String(200), nullable=True)      # Entre Calle 2
    extra_data = Column(Text, nullable=True)                   # Dato extra

    # --- Datos plan ---
    contract_date = Column(Date, nullable=True)
    is_free = Column(Boolean, default=False)                   # Conexión gratuita
    generate_month_charge = Column(Boolean, default=True)      # Generar cargo del mes (ANTENA)

    # --- IP (ambos tipos llevan IP) ---
    ip_address = Column(String(45), nullable=True)             # IP asignada
    ip_additional = Column(Text, nullable=True)                # IPs adicionales (ANTENA)
    mac_address = Column(String(17), nullable=True)            # MAC ONU/CPE para DHCP (AA:BB:CC:DD:EE:FF)

    # --- FIBRA: Red PPPoE ---
    olt_zone_id = Column(Integer, ForeignKey("olt_zones.id"), nullable=True)
    nap_id = Column(Integer, ForeignKey("naps.id"), nullable=True)
    nap_port_id = Column(Integer, ForeignKey("nap_ports.id"), nullable=True)
    pppoe_profile = Column(String(100), nullable=True)         # ej: "default-encryption"
    pppoe_username = Column(String(100), nullable=True)
    pppoe_password_encrypted = Column(Text, nullable=True)
    onu_id = Column(Integer, ForeignKey("onus.id"), nullable=True)
    mode = Column(Enum(BridgeRouterMode), nullable=True)       # Bridge / Router

    # --- ANTENA: Red estática ---
    cpe_id = Column(Integer, ForeignKey("cpes.id"), nullable=True)
    router_id = Column(Integer, ForeignKey("routers.id"), nullable=True)
    is_backbone_router = Column(Boolean, default=False)        # Router Backbone checkbox

    # --- Config avanzada ---
    api_credentials_source = Column(String(50), nullable=True)  # ONU/CPE/Célula/Config
    ipv4_mark_output = Column(String(50), default="default_main")
    custom_priority = Column(Boolean, default=False)
    signal_dbm = Column(Numeric(6, 2), nullable=True)          # Nivel señal dBm (FIBRA)

    # --- ONU autorizada ---
    onu_authorized = Column(Boolean, default=False)             # FIBRA: ONU fue autorizada
    onu_auth_frame_slot_port = Column(String(20), nullable=True)  # ej: "1/4/4"
    onu_auth_olt_id = Column(Integer, nullable=True)
    onu_auth_line_profile = Column(String(100), nullable=True)
    onu_auth_remote_profile = Column(String(100), nullable=True)
    onu_auth_vlan = Column(String(20), nullable=True)           # ej: "100"

    # --- Latencia (monitoreo) ---
    latency_ms = Column(Numeric(8, 2), nullable=True)

    # --- Coordenadas ---
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)

    # --- Baja ---
    cancel_reason = Column(Enum(CancelReason), nullable=True)
    cancel_detail = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # --- Relationships ---
    tenant = relationship("Tenant", back_populates="connections")
    client = relationship("Client", back_populates="connections")
    cell = relationship("Cell", back_populates="connections")
    service_plan = relationship("ServicePlan", back_populates="connections")
    olt_zone = relationship("OltZone", foreign_keys=[olt_zone_id])
    nap = relationship("Nap", foreign_keys=[nap_id])
    nap_port = relationship("NapPort", foreign_keys=[nap_port_id])
    onu = relationship("Onu", foreign_keys=[onu_id])
    cpe = relationship("Cpe", foreign_keys=[cpe_id])
    router = relationship("Router", foreign_keys=[router_id])

    def __repr__(self):
        return f"<Connection {self.id} {self.connection_type.value} ({self.status.value})>"
