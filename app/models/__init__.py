"""
Sistema ISP - Models
Importa todos los modelos para que SQLAlchemy los registre.
"""
# Base
from app.models.base import TenantBase, TimestampMixin

# Core
from app.models.tenant import Tenant, TenantPlan, TenantStatus
from app.models.user import User, UserRole
from app.models.mikrotik import TenantMikrotik

# Clientes y Prospectos
from app.models.client import Client, ClientType, ClientStatus
from app.models.prospect import Prospect, ProspectStatus, InstallationType, ProspectFollowUp

# Archivo Cliente 
from app.models.client_file import ClientFile, FileCategory

# Células y Red
from app.models.cell import Cell, CellType, AddressAssignment
from app.models.olt import OltConfig
from app.models.network import OltZone, Nap, NapPort

# Planes
from app.models.plan import ServicePlan, PlanType, CellPlan, CellInterface

# Conexiones
from app.models.connection import Connection, ConnectionType, ConnectionStatus, BridgeRouterMode, CancelReason

# Tickets
from app.models.ticket import Ticket, TicketNote, TicketType, TicketStatus, TicketPriority

# Inventario
from app.models.inventory import (
    Brand, DeviceModel, Supplier, MerchandiseReception,
    Onu, Cpe, Router
)

# Auxiliares
from app.models.auxiliary import OltProfile, ProfileType, ClientTag

# Facturación (PASO 4)
from app.models.billing import BillingGroup, TapipayConfig, Invoice, Payment

# WhatsApp
from app.models.whatsapp import (
    WhatsappConfig, WhatsappConversation, WhatsappMessage,
    MessageDirection, MessageType, MessageStatus, ConversationStatus
)
# Pasarelas de Pago
from app.models.payment_gateway import PaymentGatewayConfig, GatewayType

# Localidades
from app.models.locality import Locality

__all__ = [
    # Base
    "TenantBase", "TimestampMixin",
    # Core
    "Tenant", "TenantPlan", "TenantStatus",
    "User", "UserRole",
    "TenantMikrotik",
    # Clientes
    "Client", "ClientType", "ClientStatus",
    "Prospect", "ProspectStatus", "InstallationType", "ProspectFollowUp",
    "ClientFile", "FileCategory",
    # Células
    "Cell", "CellType", "AddressAssignment",
    "OltConfig",
    "OltZone", "Nap", "NapPort",
    # Planes
    "ServicePlan", "PlanType", "CellPlan", "CellInterface",
    # Conexiones
    "Connection", "ConnectionType", "ConnectionStatus", "BridgeRouterMode", "CancelReason",
    # Inventario
    "Brand", "DeviceModel", "Supplier", "MerchandiseReception",
    "Onu", "Cpe", "Router",
    # Auxiliares
    "OltProfile", "ProfileType", "ClientTag",
    # Tickets
    "Ticket", "TicketNote", "TicketType", "TicketStatus", "TicketPriority",
    # WhatsApp
    "WhatsappConfig", "WhatsappConversation", "WhatsappMessage",
    "MessageDirection", "MessageType", "MessageStatus", "ConversationStatus",
    # Pasarelas de Pago
    "PaymentGatewayConfig", "GatewayType",
    # Localidades
    "Locality",
]
