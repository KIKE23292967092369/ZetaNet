"""
Sistema ISP - Router: WhatsApp Live Chat
Integración con Gupshup para enviar/recibir mensajes WhatsApp.
Chat en vivo desde la plataforma.

Endpoints:
  CONFIG:
    POST   /whatsapp/config              → Configurar Gupshup
    GET    /whatsapp/config              → Ver configuración
    PATCH  /whatsapp/config/{id}         → Actualizar configuración
    POST   /whatsapp/config/test         → Probar conexión

  CONVERSACIONES:
    GET    /whatsapp/conversations                    → Bandeja (listar)
    GET    /whatsapp/conversations/{id}               → Ver conversación con mensajes
    POST   /whatsapp/conversations/{id}/send          → Enviar mensaje
    PATCH  /whatsapp/conversations/{id}               → Marcar leída / cerrar
    POST   /whatsapp/conversations/{id}/link-client   → Vincular con cliente

  WEBHOOK:
    POST   /webhooks/whatsapp            → Recibir mensajes de Gupshup
"""
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.client import Client
from app.models.whatsapp import (
    WhatsappConfig, WhatsappConversation, WhatsappMessage,
    MessageDirection, MessageType, MessageStatus, ConversationStatus
)
from app.schemas.whatsapp import (
    WhatsappConfigCreate, WhatsappConfigUpdate, WhatsappConfigResponse,
    SendMessageRequest, MessageResponse,
    ConversationListResponse, ConversationDetailResponse,
    LinkClientRequest
)

logger = logging.getLogger("whatsapp")

# ================================================================
# ROUTERS (2 routers: uno autenticado, uno público para webhook)
# ================================================================

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

GUPSHUP_API_URL = "https://api.gupshup.io/wa/api/v1/msg"


# ================================================================
# HELPER: Obtener config de WhatsApp del tenant
# ================================================================

async def _get_whatsapp_config(tenant_id: int, db: AsyncSession) -> WhatsappConfig:
    """Obtiene la configuración de WhatsApp del tenant."""
    result = await db.execute(
        select(WhatsappConfig).where(
            WhatsappConfig.tenant_id == tenant_id,
            WhatsappConfig.is_active == True
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(400, "WhatsApp no configurado. Configure Gupshup primero.")
    return config


async def _find_or_create_conversation(
    db: AsyncSession,
    tenant_id: int,
    phone_number: str,
    contact_name: str = None
) -> WhatsappConversation:
    """Busca conversación existente o crea una nueva."""
    result = await db.execute(
        select(WhatsappConversation).where(
            WhatsappConversation.tenant_id == tenant_id,
            WhatsappConversation.phone_number == phone_number
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        # Auto-vincular si el número coincide con un cliente
        client_id = None
        client_result = await db.execute(
            select(Client).where(
                Client.tenant_id == tenant_id,
                Client.phone_cell == phone_number
            )
        )
        client = client_result.scalar_one_or_none()
        if client:
            client_id = client.id
            if not contact_name:
                contact_name = f"{client.first_name} {client.last_name}"

        conversation = WhatsappConversation(
            tenant_id=tenant_id,
            phone_number=phone_number,
            contact_name=contact_name,
            client_id=client_id,
            status=ConversationStatus.ACTIVA,
            unread_count=0,
        )
        db.add(conversation)
        await db.flush()

    return conversation


# ================================================================
# CONFIG
# ================================================================

@router.post("/config", response_model=WhatsappConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_whatsapp_config(
    data: WhatsappConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Configurar integración con Gupshup WhatsApp."""
    # Verificar que no exista config activa
    existing = await db.execute(
        select(WhatsappConfig).where(
            WhatsappConfig.tenant_id == user.tenant_id,
            WhatsappConfig.is_active == True
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Ya existe una configuración de WhatsApp activa")

    config = WhatsappConfig(
        tenant_id=user.tenant_id,
        api_key=data.api_key,
        app_name=data.app_name,
        source_phone=data.source_phone,
        webhook_secret=data.webhook_secret,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/config", response_model=WhatsappConfigResponse)
async def get_whatsapp_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ver configuración de WhatsApp del tenant."""
    config = await _get_whatsapp_config(user.tenant_id, db)
    return config


@router.patch("/config/{config_id}", response_model=WhatsappConfigResponse)
async def update_whatsapp_config(
    config_id: int,
    data: WhatsappConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Actualizar configuración de WhatsApp."""
    result = await db.execute(
        select(WhatsappConfig).where(
            WhatsappConfig.id == config_id,
            WhatsappConfig.tenant_id == user.tenant_id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Configuración no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.post("/config/test")
async def test_whatsapp_connection(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Probar conexión con Gupshup API."""
    config = await _get_whatsapp_config(user.tenant_id, db)

    try:
        async with httpx.AsyncClient() as client:
            # Gupshup health check - listar templates
            response = await client.get(
                f"https://api.gupshup.io/wa/app/{config.app_name}/template/list",
                headers={"apikey": config.api_key},
                timeout=10,
            )

            if response.status_code == 200:
                return {
                    "connected": True,
                    "app_name": config.app_name,
                    "source_phone": config.source_phone,
                    "message": "Conexión exitosa con Gupshup"
                }
            else:
                return {
                    "connected": False,
                    "error": f"Gupshup respondió {response.status_code}: {response.text}"
                }
    except Exception as e:
        return {"connected": False, "error": str(e)}


# ================================================================
# CONVERSACIONES
# ================================================================

@router.get("/conversations", response_model=List[ConversationListResponse])
async def list_conversations(
    status_filter: Optional[ConversationStatus] = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Bandeja de conversaciones WhatsApp.
    Ordenadas por último mensaje (más recientes primero).
    """
    query = select(WhatsappConversation).where(
        WhatsappConversation.tenant_id == user.tenant_id
    )

    if status_filter:
        query = query.where(WhatsappConversation.status == status_filter)

    if unread_only:
        query = query.where(WhatsappConversation.unread_count > 0)

    query = query.order_by(desc(WhatsappConversation.last_message_at))
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    conversations = result.scalars().all()

    # Agregar nombre del cliente si está vinculado
    response = []
    for conv in conversations:
        conv_dict = {
            "id": conv.id,
            "phone_number": conv.phone_number,
            "contact_name": conv.contact_name,
            "client_id": conv.client_id,
            "client_name": None,
            "status": conv.status,
            "unread_count": conv.unread_count,
            "last_message_at": conv.last_message_at,
            "last_message_preview": conv.last_message_preview,
            "created_at": conv.created_at,
        }

        if conv.client_id:
            client = await db.get(Client, conv.client_id)
            if client:
                conv_dict["client_name"] = f"{client.first_name} {client.last_name}"

        response.append(conv_dict)

    return response


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ver una conversación con todos sus mensajes."""
    result = await db.execute(
        select(WhatsappConversation)
        .options(selectinload(WhatsappConversation.messages))
        .where(
            WhatsappConversation.id == conversation_id,
            WhatsappConversation.tenant_id == user.tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(404, "Conversación no encontrada")

    # Marcar como leída
    conversation.unread_count = 0
    await db.commit()

    # Nombre del cliente
    client_name = None
    if conversation.client_id:
        client = await db.get(Client, conversation.client_id)
        if client:
            client_name = f"{client.first_name} {client.last_name}"

    return {
        "id": conversation.id,
        "phone_number": conversation.phone_number,
        "contact_name": conversation.contact_name,
        "client_id": conversation.client_id,
        "client_name": client_name,
        "status": conversation.status,
        "unread_count": 0,
        "messages": conversation.messages,
    }


@router.post("/conversations/{conversation_id}/send", response_model=MessageResponse)
async def send_message(
    conversation_id: int,
    data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Enviar mensaje WhatsApp al cliente desde la plataforma.
    Usa Gupshup API para entregar el mensaje.
    """
    # Obtener conversación
    result = await db.execute(
        select(WhatsappConversation).where(
            WhatsappConversation.id == conversation_id,
            WhatsappConversation.tenant_id == user.tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(404, "Conversación no encontrada")

    # Obtener config
    config = await _get_whatsapp_config(user.tenant_id, db)

    # Enviar vía Gupshup
    gupshup_message_id = None
    send_status = MessageStatus.SENT

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "channel": "whatsapp",
                "source": config.source_phone,
                "destination": conversation.phone_number,
                "message": '{"type":"text","text":"' + data.message + '"}',
                "src.name": config.app_name,
            }

            response = await client.post(
                GUPSHUP_API_URL,
                data=payload,
                headers={"apikey": config.api_key},
                timeout=15,
            )

            if response.status_code == 200:
                resp_data = response.json()
                gupshup_message_id = resp_data.get("messageId")
                send_status = MessageStatus.SENT
            else:
                logger.error(f"Gupshup error: {response.status_code} {response.text}")
                send_status = MessageStatus.FAILED

    except Exception as e:
        logger.error(f"Error enviando WhatsApp: {e}")
        send_status = MessageStatus.FAILED

    # Guardar mensaje en BD
    message = WhatsappMessage(
        tenant_id=user.tenant_id,
        conversation_id=conversation.id,
        direction=MessageDirection.OUTBOUND,
        message_type=data.message_type,
        content=data.message,
        gupshup_message_id=gupshup_message_id,
        status=send_status,
        sent_by=user.id,
    )
    db.add(message)

    # Actualizar conversación
    conversation.last_message_at = message.created_at
    conversation.last_message_preview = data.message[:300]

    await db.commit()
    await db.refresh(message)

    if send_status == MessageStatus.FAILED:
        raise HTTPException(502, "Error al enviar mensaje por WhatsApp")

    return message


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    status_update: Optional[ConversationStatus] = None,
    mark_read: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Actualizar conversación: marcar como leída o cambiar estado."""
    result = await db.execute(
        select(WhatsappConversation).where(
            WhatsappConversation.id == conversation_id,
            WhatsappConversation.tenant_id == user.tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(404, "Conversación no encontrada")

    if mark_read:
        conversation.unread_count = 0

    if status_update:
        conversation.status = status_update

    await db.commit()
    return {"message": "Conversación actualizada"}


@router.post("/conversations/{conversation_id}/link-client")
async def link_conversation_to_client(
    conversation_id: int,
    data: LinkClientRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Vincular una conversación con un cliente existente."""
    # Verificar conversación
    result = await db.execute(
        select(WhatsappConversation).where(
            WhatsappConversation.id == conversation_id,
            WhatsappConversation.tenant_id == user.tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(404, "Conversación no encontrada")

    # Verificar cliente
    client = await db.get(Client, data.client_id)
    if not client or client.tenant_id != user.tenant_id:
        raise HTTPException(404, "Cliente no encontrado")

    conversation.client_id = data.client_id
    conversation.contact_name = f"{client.first_name} {client.last_name}"

    await db.commit()
    return {
        "message": f"Conversación vinculada a {client.first_name} {client.last_name}",
        "client_id": client.id
    }


# ================================================================
# WEBHOOK (público - Gupshup envía mensajes aquí)
# ================================================================

@webhook_router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook para recibir mensajes de Gupshup.
    Gupshup envía aquí cada mensaje que un cliente manda por WhatsApp.
    Este endpoint es PÚBLICO (sin JWT).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    event_type = body.get("type", "")
    payload = body.get("payload", {})

    # --- Mensaje entrante ---
    if event_type == "message":
        sender_phone = payload.get("source", "")
        sender_name = payload.get("sender", {}).get("name", "")
        msg_type = payload.get("type", "text")
        msg_id = payload.get("id", "")

        # Extraer contenido según tipo
        content = ""
        media_url = None
        media_filename = None

        if msg_type == "text":
            content = payload.get("payload", {}).get("text", "")
        elif msg_type in ("image", "document", "audio", "video"):
            content = payload.get("payload", {}).get("caption", "")
            media_url = payload.get("payload", {}).get("url", "")
            media_filename = payload.get("payload", {}).get("name", "")
        elif msg_type == "location":
            loc = payload.get("payload", {})
            content = f"📍 {loc.get('latitude', '')}, {loc.get('longitude', '')}"

        if not sender_phone:
            return {"status": "ignored", "reason": "no sender phone"}

        # Determinar tenant por el número destino (source_phone del config)
        dest_phone = payload.get("destination", "")
        config_result = await db.execute(
            select(WhatsappConfig).where(
                WhatsappConfig.source_phone == dest_phone,
                WhatsappConfig.is_active == True
            )
        )
        config = config_result.scalar_one_or_none()

        if not config:
            logger.warning(f"Webhook WhatsApp: no config para número {dest_phone}")
            return {"status": "ignored", "reason": "no config found"}

        tenant_id = config.tenant_id

        # Buscar o crear conversación
        conversation = await _find_or_create_conversation(
            db, tenant_id, sender_phone, sender_name
        )

        # Mapear tipo de mensaje
        type_map = {
            "text": MessageType.TEXT,
            "image": MessageType.IMAGE,
            "document": MessageType.DOCUMENT,
            "audio": MessageType.AUDIO,
            "video": MessageType.VIDEO,
            "location": MessageType.LOCATION,
            "sticker": MessageType.STICKER,
        }

        # Guardar mensaje
        message = WhatsappMessage(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            message_type=type_map.get(msg_type, MessageType.TEXT),
            content=content,
            media_url=media_url,
            media_filename=media_filename,
            gupshup_message_id=msg_id,
            status=MessageStatus.DELIVERED,
        )
        db.add(message)

        # Actualizar conversación
        conversation.unread_count = (conversation.unread_count or 0) + 1
        conversation.last_message_at = func.now()
        conversation.last_message_preview = content[:300] if content else f"[{msg_type}]"

        if sender_name and not conversation.contact_name:
            conversation.contact_name = sender_name

        await db.commit()

        logger.info(f"WhatsApp inbound: {sender_phone} → tenant {tenant_id}")
        return {"status": "ok", "message_id": message.id}

    # --- Evento de estado (delivered, read) ---
    elif event_type == "message-event":
        event_status = payload.get("type", "")
        gupshup_id = payload.get("id", "")

        if gupshup_id and event_status in ("delivered", "read"):
            status_map = {
                "delivered": MessageStatus.DELIVERED,
                "read": MessageStatus.READ,
            }
            await db.execute(
                update(WhatsappMessage)
                .where(WhatsappMessage.gupshup_message_id == gupshup_id)
                .values(status=status_map[event_status])
            )
            await db.commit()

        return {"status": "ok", "event": event_status}

    return {"status": "ignored", "type": event_type}


# Necesario importar func para last_message_at
from sqlalchemy import func