"""
Sistema ISP - Router: Payment Gateways
Configuración multi-pasarela y generación de cobros.

CONFIG:
  POST   /payment-gateways/                  → Configurar pasarela
  GET    /payment-gateways/                  → Listar configuradas
  GET    /payment-gateways/supported         → Ver pasarelas soportadas
  PATCH  /payment-gateways/{id}              → Actualizar
  DELETE /payment-gateways/{id}              → Eliminar
  POST   /payment-gateways/{id}/test         → Probar conexión
  POST   /payment-gateways/{id}/default      → Marcar como default

COBROS:
  POST   /payment-gateways/create-charge     → Crear cobro con la pasarela default

WEBHOOKS:
  POST   /webhooks/conekta                   → Webhook Conekta
  POST   /webhooks/stripe                    → Webhook Stripe
  POST   /webhooks/openpay                   → Webhook OpenPay
  POST   /webhooks/mercadopago               → Webhook Mercado Pago
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.client import Client
from app.models.payment_gateway import PaymentGatewayConfig, GatewayType
from app.schemas.payment_gateway import (
    GatewayConfigCreate, GatewayConfigUpdate, GatewayConfigResponse,
    CreateChargeRequest, ChargeResponse,
)
from app.services.payments.payment_base import PaymentCredentials
from app.services.payments.payment_factory import get_payment_driver, get_supported_gateways

logger = logging.getLogger("payment_gateways")

router = APIRouter(prefix="/payment-gateways", tags=["Pasarelas de Pago"])
webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ================================================================
# HELPER
# ================================================================

async def _get_gateway_config(gateway_id: int, tenant_id: int, db: AsyncSession) -> PaymentGatewayConfig:
    result = await db.execute(
        select(PaymentGatewayConfig).where(
            PaymentGatewayConfig.id == gateway_id,
            PaymentGatewayConfig.tenant_id == tenant_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Pasarela no encontrada")
    return config


async def _get_default_gateway(tenant_id: int, db: AsyncSession) -> PaymentGatewayConfig:
    result = await db.execute(
        select(PaymentGatewayConfig).where(
            PaymentGatewayConfig.tenant_id == tenant_id,
            PaymentGatewayConfig.is_default == True,
            PaymentGatewayConfig.is_active == True,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(400, "No hay pasarela de pago configurada como default")
    return config


def _build_credentials(config: PaymentGatewayConfig) -> PaymentCredentials:
    return PaymentCredentials(
        gateway_type=config.gateway_type.value,
        api_key=config.api_key,
        secret_key=config.secret_key or "",
        merchant_id=config.merchant_id or "",
        webhook_secret=config.webhook_secret or "",
        currency=config.currency,
        environment=config.environment,
    )


# ================================================================
# CONFIG
# ================================================================

@router.get("/supported")
async def list_supported_gateways():
    """Ver pasarelas de pago soportadas por el sistema."""
    return get_supported_gateways()


@router.post("/", response_model=GatewayConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_gateway_config(
    data: GatewayConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Configurar una nueva pasarela de pago."""
    # Verificar que no exista una del mismo tipo activa
    existing = await db.execute(
        select(PaymentGatewayConfig).where(
            PaymentGatewayConfig.tenant_id == user.tenant_id,
            PaymentGatewayConfig.gateway_type == data.gateway_type,
            PaymentGatewayConfig.is_active == True,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Ya existe una configuración activa de {data.gateway_type.value}")

    # Si es la primera, marcar como default
    any_existing = await db.execute(
        select(PaymentGatewayConfig).where(
            PaymentGatewayConfig.tenant_id == user.tenant_id,
            PaymentGatewayConfig.is_active == True,
        )
    )
    is_first = any_existing.scalar_one_or_none() is None

    config = PaymentGatewayConfig(
        tenant_id=user.tenant_id,
        gateway_type=data.gateway_type,
        api_key=data.api_key,
        secret_key=data.secret_key,
        merchant_id=data.merchant_id,
        webhook_secret=data.webhook_secret,
        display_name=data.display_name or data.gateway_type.value.title(),
        currency=data.currency,
        environment=data.environment,
        is_default=is_first,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/", response_model=List[GatewayConfigResponse])
async def list_gateway_configs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Listar pasarelas de pago configuradas."""
    result = await db.execute(
        select(PaymentGatewayConfig).where(
            PaymentGatewayConfig.tenant_id == user.tenant_id
        )
    )
    return result.scalars().all()


@router.patch("/{gateway_id}", response_model=GatewayConfigResponse)
async def update_gateway_config(
    gateway_id: int,
    data: GatewayConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Actualizar configuración de pasarela."""
    config = await _get_gateway_config(gateway_id, user.tenant_id, db)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{gateway_id}")
async def delete_gateway_config(
    gateway_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Eliminar configuración de pasarela."""
    config = await _get_gateway_config(gateway_id, user.tenant_id, db)
    await db.delete(config)
    await db.commit()
    return {"message": f"Pasarela {config.gateway_type.value} eliminada"}


@router.post("/{gateway_id}/test")
async def test_gateway_connection(
    gateway_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Probar conexión con la pasarela de pago."""
    config = await _get_gateway_config(gateway_id, user.tenant_id, db)
    credentials = _build_credentials(config)
    driver = get_payment_driver(credentials)
    result = await driver.test_connection()
    return result


@router.post("/{gateway_id}/default")
async def set_default_gateway(
    gateway_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Marcar una pasarela como la default del tenant."""
    config = await _get_gateway_config(gateway_id, user.tenant_id, db)

    # Quitar default de todas las demás
    await db.execute(
        update(PaymentGatewayConfig)
        .where(
            PaymentGatewayConfig.tenant_id == user.tenant_id,
            PaymentGatewayConfig.id != gateway_id,
        )
        .values(is_default=False)
    )

    config.is_default = True
    await db.commit()

    return {"message": f"{config.gateway_type.value} es ahora la pasarela por defecto"}


# ================================================================
# CREAR COBRO
# ================================================================

@router.post("/create-charge", response_model=ChargeResponse)
async def create_charge(
    data: CreateChargeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Crear un cobro usando la pasarela default del tenant.
    Genera link de pago para enviar al cliente.
    """
    # Obtener pasarela default
    gateway_config = await _get_default_gateway(user.tenant_id, db)
    credentials = _build_credentials(gateway_config)
    driver = get_payment_driver(credentials)

    # Obtener datos del cliente
    client = await db.get(Client, data.client_id)
    if not client or client.tenant_id != user.tenant_id:
        raise HTTPException(404, "Cliente no encontrado")

    customer_name = data.customer_name or f"{client.first_name} {client.last_name}"
    customer_email = data.customer_email or (client.email if hasattr(client, 'email') else "")
    customer_phone = data.customer_phone or client.phone_cell or ""

    # Crear cobro en la pasarela
    result = await driver.create_charge(
        amount=data.amount,
        description=data.description,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        reference_id=str(data.invoice_id or ""),
        metadata={"client_id": data.client_id, "tenant_id": user.tenant_id},
    )

    if not result.success:
        raise HTTPException(502, f"Error en {gateway_config.gateway_type.value}: {result.error}")

    return ChargeResponse(
        gateway=gateway_config.gateway_type.value,
        charge_id=result.charge_id,
        payment_url=result.payment_url,
        status=result.status,
        amount=data.amount,
        currency=gateway_config.currency,
        reference=result.reference,
        barcode_url=result.barcode_url,
        expires_at=result.expires_at,
    )


# ================================================================
# WEBHOOKS (públicos - las pasarelas envían aquí)
# ================================================================

async def _process_payment_webhook(
    gateway_type: str,
    body: dict,
    db: AsyncSession,
):
    """Procesa webhook de cualquier pasarela de forma genérica."""
    # Buscar config por tipo de pasarela
    result = await db.execute(
        select(PaymentGatewayConfig).where(
            PaymentGatewayConfig.gateway_type == gateway_type,
            PaymentGatewayConfig.is_active == True,
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        logger.warning(f"Webhook {gateway_type}: no hay config activa")
        return {"status": "ignored", "reason": "no config"}

    credentials = _build_credentials(config)
    driver = get_payment_driver(credentials)

    # Parsear webhook
    parsed = driver.parse_webhook(body)
    logger.info(f"Webhook {gateway_type}: {parsed}")

    # Si el pago fue exitoso, registrar en billing
    if parsed.get("status") in ("paid", "approved", "completed", "charge.succeeded"):
        # Aquí puedes conectar con tu módulo de billing existente
        # para registrar el pago automáticamente
        logger.info(
            f"Pago confirmado via {gateway_type}: "
            f"charge={parsed.get('charge_id')}, amount={parsed.get('amount')}"
        )
        # TODO: Llamar a billing para registrar pago automático
        # await register_payment(db, config.tenant_id, parsed)

    return {"status": "ok", "event": parsed.get("event")}


@webhook_router.post("/conekta")
async def conekta_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook para Conekta."""
    body = await request.json()
    return await _process_payment_webhook("conekta", body, db)


@webhook_router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook para Stripe."""
    body = await request.json()
    return await _process_payment_webhook("stripe", body, db)


@webhook_router.post("/openpay")
async def openpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook para OpenPay."""
    body = await request.json()
    return await _process_payment_webhook("openpay", body, db)


@webhook_router.post("/mercadopago")
async def mercadopago_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook para Mercado Pago."""
    body = await request.json()
    return await _process_payment_webhook("mercadopago", body, db)