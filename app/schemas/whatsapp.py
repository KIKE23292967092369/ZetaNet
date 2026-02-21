"""
Sistema ISP - Schemas: WhatsApp
Schemas para configuración, conversaciones y mensajes.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.whatsapp import (
    MessageDirection, MessageType, MessageStatus, ConversationStatus
)


# ================================================================
# CONFIG
# ================================================================

class WhatsappConfigCreate(BaseModel):
    api_key: str = Field(..., min_length=1)
    app_name: str = Field(..., max_length=200)
    source_phone: str = Field(..., max_length=20)      # "5219511234567"
    webhook_secret: Optional[str] = None


class WhatsappConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    app_name: Optional[str] = None
    source_phone: Optional[str] = None
    webhook_secret: Optional[str] = None
    is_active: Optional[bool] = None


class WhatsappConfigResponse(BaseModel):
    id: int
    app_name: str
    source_phone: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ================================================================
# MENSAJES
# ================================================================

class SendMessageRequest(BaseModel):
    """Para enviar mensaje desde la plataforma al cliente."""
    message: str = Field(..., min_length=1, max_length=4096)
    message_type: MessageType = MessageType.TEXT


class MessageResponse(BaseModel):
    id: int
    direction: MessageDirection
    message_type: MessageType
    content: Optional[str]
    media_url: Optional[str]
    media_filename: Optional[str]
    status: MessageStatus
    sent_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ================================================================
# CONVERSACIONES
# ================================================================

class ConversationListResponse(BaseModel):
    id: int
    phone_number: str
    contact_name: Optional[str]
    client_id: Optional[int]
    client_name: Optional[str] = None
    status: ConversationStatus
    unread_count: int
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: int
    phone_number: str
    contact_name: Optional[str]
    client_id: Optional[int]
    client_name: Optional[str] = None
    status: ConversationStatus
    unread_count: int
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


class LinkClientRequest(BaseModel):
    """Vincular conversación con un cliente existente."""
    client_id: int


# ================================================================
# WEBHOOK GUPSHUP (lo que recibimos)
# ================================================================

class GupshupWebhookPayload(BaseModel):
    """Payload que Gupshup envía a nuestro webhook."""
    type: Optional[str] = None                 # "message", "message-event"
    payload: Optional[dict] = None             # Contenido del mensaje
    app: Optional[str] = None                  # Nombre de la app