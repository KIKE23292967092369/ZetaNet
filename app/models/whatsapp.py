"""
Sistema ISP - Modelo: WhatsApp
Configuración Gupshup, conversaciones y mensajes.
Chat en vivo desde la plataforma con clientes por WhatsApp.
"""
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime,
    ForeignKey, Enum, func
)
from sqlalchemy.orm import relationship
from app.models.base import TenantBase


# ================================================================
# ENUMS
# ================================================================

class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"      # Cliente → Plataforma
    OUTBOUND = "outbound"    # Plataforma → Cliente


class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    STICKER = "sticker"


class MessageStatus(str, enum.Enum):
    SENT = "sent"            # Enviado a Gupshup
    DELIVERED = "delivered"  # Entregado al cliente
    READ = "read"            # Leído por cliente
    FAILED = "failed"        # Error al enviar


class ConversationStatus(str, enum.Enum):
    ACTIVA = "activa"
    CERRADA = "cerrada"


# ================================================================
# CONFIG GUPSHUP (por tenant)
# ================================================================

class WhatsappConfig(TenantBase):
    __tablename__ = "whatsapp_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Gupshup API ---
    api_key = Column(Text, nullable=False)                     # API Key de Gupshup
    app_name = Column(String(200), nullable=False)             # Nombre de la app en Gupshup
    source_phone = Column(String(20), nullable=False)          # Número del ISP (ej: "5219511234567")

    # --- Webhook ---
    webhook_secret = Column(String(200), nullable=True)        # Para verificar webhooks

    # --- Estado ---
    is_active = Column(Boolean, default=True)

    # --- Relationships ---
    tenant = relationship("Tenant", backref="whatsapp_config")

    def __repr__(self):
        return f"<WhatsappConfig {self.source_phone} ({self.app_name})>"


# ================================================================
# CONVERSACIONES
# ================================================================

class WhatsappConversation(TenantBase):
    __tablename__ = "whatsapp_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Contacto ---
    phone_number = Column(String(20), nullable=False, index=True)   # Número del cliente
    contact_name = Column(String(200), nullable=True)               # Nombre del contacto en WhatsApp

    # --- Vinculación con cliente ---
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    # --- Estado ---
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVA, nullable=False)
    unread_count = Column(Integer, default=0)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_preview = Column(String(300), nullable=True)       # Preview del último mensaje

    # --- Relationships ---
    tenant = relationship("Tenant", backref="whatsapp_conversations")
    client = relationship("Client", backref="whatsapp_conversations")
    messages = relationship(
        "WhatsappMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="WhatsappMessage.created_at.asc()"
    )

    def __repr__(self):
        return f"<Conversation {self.phone_number} ({self.status.value})>"


# ================================================================
# MENSAJES
# ================================================================

class WhatsappMessage(TenantBase):
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # --- Mensaje ---
    direction = Column(Enum(MessageDirection), nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False)
    content = Column(Text, nullable=True)                      # Texto del mensaje
    media_url = Column(Text, nullable=True)                    # URL de imagen/audio/doc
    media_filename = Column(String(255), nullable=True)        # Nombre del archivo

    # --- Gupshup ---
    gupshup_message_id = Column(String(200), nullable=True)    # ID del mensaje en Gupshup
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT, nullable=False)

    # --- Quién envió (si es outbound) ---
    sent_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # --- Relationships ---
    conversation = relationship("WhatsappConversation", back_populates="messages")
    sender = relationship("User", backref="whatsapp_messages")

    def __repr__(self):
        return f"<Message {self.direction.value} ({self.message_type.value})>"