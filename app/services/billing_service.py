"""
Sistema ISP - Servicio de Facturación
Genera facturas, procesa pagos, genera recargos, suspende/reactiva.

Recargo automático:
  - CON_PLAN: No pagó el día de corte → al día siguiente se genera
    factura extra de $50 (configurable). Ejecutar diariamente.
  - PREPAGO: No se genera recargo. Puede pagar cuando quiera.
  - Ambos tipos se suspenden si no pagan después de los días de gracia.
"""
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from calendar import monthrange

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.billing import (
    BillingGroup, TapipayConfig, Invoice, Payment,
    InvoiceStatus, InvoiceType, PaymentStatus, PaymentMethod
)
from app.models.client import Client, ClientType
from app.models.connection import Connection, ConnectionStatus
from app.models.plan import ServicePlan
from app.services.tapipay_service import TapipayService, TapipayError
from app.services.mikrotik_helper import (
    suspend_connection_mikrotik,
    reactivate_connection_mikrotik
)

logger = logging.getLogger("billing_service")

MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def generate_tapipay_identifier(client_id: int) -> str:
    return f"CLI-{str(client_id).zfill(5)}"


async def get_tapipay_service(db: AsyncSession, tenant_id: int) -> TapipayService:
    result = await db.execute(
        select(TapipayConfig).where(
            TapipayConfig.tenant_id == tenant_id,
            TapipayConfig.is_active == True
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise TapipayError("No hay configuración de tapipay. Configúrela primero.")

    return TapipayService(
        api_key=config.api_key,
        username=config.username,
        password=config.password,
        company_code=config.company_code,
        company_slug=config.company_slug,
        environment=config.environment,
        modality_id_digital=config.modality_id_digital or "",
        modality_id_cash=config.modality_id_cash or "",
        identifier_name_digital=config.identifier_name_digital or "",
        identifier_name_cash=config.identifier_name_cash or "",
    )


# ================================================================
# GENERAR FACTURAS MENSUALES
# ================================================================

async def generate_invoices_for_group(
    db: AsyncSession, tenant_id: int, billing_group_id: int,
    period_month: int, period_year: int, sync_tapipay: bool = True
) -> Dict[str, Any]:
    """Genera facturas mensuales para todos los clientes activos de un grupo."""
    group = await db.get(BillingGroup, billing_group_id)
    if not group or group.tenant_id != tenant_id:
        raise ValueError("Grupo de corte no encontrado")

    period_label = f"{MONTHS_ES.get(period_month, '')} {period_year}"

    # Clientes activos del grupo con conexiones activas
    result = await db.execute(
        select(Client, Connection, ServicePlan)
        .join(Connection, and_(
            Connection.client_id == Client.id,
            Connection.is_active == True,
            Connection.status == ConnectionStatus.ACTIVE
        ))
        .join(ServicePlan, Connection.plan_id == ServicePlan.id)
        .where(
            Client.tenant_id == tenant_id,
            Client.billing_group_id == billing_group_id,
            Client.is_active == True
        )
    )
    rows = result.all()

    if not rows:
        return {"billing_group": group.name, "period": period_label,
                "invoices_created": 0, "invoices_synced_tapipay": 0,
                "errors": ["No hay clientes activos en este grupo"]}

    # Fechas
    _, last_day = monthrange(period_year, period_month)
    due_day = min(group.cutoff_day, last_day)
    due_date = date(period_year, period_month, due_day)
    suspension_date = due_date + timedelta(days=group.grace_days)

    created = 0
    synced = 0
    errors = []

    tapipay = None
    if sync_tapipay:
        try:
            tapipay = await get_tapipay_service(db, tenant_id)
        except TapipayError as e:
            errors.append(f"tapipay no disponible: {e}")
            sync_tapipay = False

    for client, connection, plan in rows:
        try:
            # No duplicar facturas
            existing = await db.execute(
                select(Invoice).where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.client_id == client.id,
                    Invoice.connection_id == connection.id,
                    Invoice.period_month == period_month,
                    Invoice.period_year == period_year,
                    Invoice.invoice_type == InvoiceType.MONTHLY,
                    Invoice.is_active == True
                )
            )
            if existing.scalar_one_or_none():
                errors.append(f"Cliente {client.id}: ya tiene factura de {period_label}")
                continue

            # Generar identifier tapipay si no tiene
            if not client.tapipay_identifier:
                client.tapipay_identifier = generate_tapipay_identifier(client.id)
            if not client.payment_link and tapipay:
                client.payment_link = tapipay.get_payment_link(client.tapipay_identifier)

            # Crear factura
            ext_req_id = str(uuid.uuid4())
            invoice = Invoice(
                tenant_id=tenant_id, client_id=client.id,
                connection_id=connection.id, billing_group_id=billing_group_id,
                invoice_type=InvoiceType.MONTHLY,
                period_month=period_month, period_year=period_year,
                period_label=period_label, amount=plan.price, amount_paid=0.0,
                currency="MXN", status=InvoiceStatus.PENDING,
                due_date=due_date, suspension_date=suspension_date,
                tapipay_external_request_id=ext_req_id,
                payment_link=client.payment_link,
            )
            db.add(invoice)
            await db.flush()
            created += 1

            # Sincronizar con tapipay
            if sync_tapipay and tapipay:
                try:
                    tp_result = await tapipay.create_debt(
                        identifier_value=client.tapipay_identifier,
                        amount=plan.price,
                        client_name=f"{client.first_name} {client.last_name}",
                        client_email=client.email or "noemail@sistema.local",
                        client_phone=client.phone_cell or "+520000000000",
                        expiration_date=due_date.isoformat(),
                        concept=f"Internet {period_label}",
                        product=plan.name,
                        external_request_id=ext_req_id,
                    )
                    invoice.tapipay_synced = True
                    invoice.tapipay_tx = tp_result.get("tx")
                    invoice.tapipay_main_tx = tp_result.get("main_tx")
                    refs = tp_result.get("references", [])
                    for ref in refs:
                        if ref.get("status") == "success":
                            invoice.tapipay_reference_value = ref.get("value")
                            invoice.tapipay_reference_image_url = ref.get("imageUrl")
                            break
                    synced += 1
                except TapipayError as e:
                    errors.append(f"Cliente {client.id} tapipay: {e}")

        except Exception as e:
            errors.append(f"Error cliente {client.id}: {str(e)}")

    await db.commit()
    logger.info(f"Facturación {period_label} '{group.name}': {created} facturas, {synced} tapipay")
    return {"billing_group": group.name, "period": period_label,
            "invoices_created": created, "invoices_synced_tapipay": synced, "errors": errors}


# ================================================================
# GENERAR RECARGOS (SOLO CON_PLAN)
# ================================================================

async def generate_late_fees(
    db: AsyncSession, tenant_id: int, ref_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Genera recargos automáticos para clientes CON_PLAN que no pagaron a tiempo.
    Ejecutar diariamente.

    Lógica:
      - Busca facturas MENSUALES con status PENDING donde due_date < hoy
      - Si el cliente es CON_PLAN → genera factura extra tipo LATE_FEE ($50)
      - Si el cliente es PREPAGO → no genera recargo (skip)
      - Solo genera un recargo por factura (no duplica)
    """
    if not ref_date:
        ref_date = date.today()

    # Facturas mensuales pendientes cuyo día de corte ya pasó
    result = await db.execute(
        select(Invoice, Client, BillingGroup)
        .join(Client, Invoice.client_id == Client.id)
        .join(BillingGroup, Invoice.billing_group_id == BillingGroup.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == InvoiceType.MONTHLY,
            Invoice.status == InvoiceStatus.PENDING,
            Invoice.due_date < ref_date,         # Ya pasó el día de corte
            Invoice.is_active == True,
        )
    )
    rows = result.all()

    fees_generated = 0
    skipped_prepago = 0
    errors = []

    for invoice, client, group in rows:
        try:
            # PREPAGO: no se cobra recargo
            if client.client_type == ClientType.PREPAGO:
                skipped_prepago += 1
                continue

            # Verificar que no exista ya un recargo para esta factura/periodo
            existing_fee = await db.execute(
                select(Invoice).where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.client_id == client.id,
                    Invoice.period_month == invoice.period_month,
                    Invoice.period_year == invoice.period_year,
                    Invoice.invoice_type == InvoiceType.LATE_FEE,
                    Invoice.is_active == True
                )
            )
            if existing_fee.scalar_one_or_none():
                continue  # Ya tiene recargo, no duplicar

            # Crear factura de recargo
            fee_amount = group.reconnection_fee  # $50 por default
            period_label = f"Recargo {MONTHS_ES.get(invoice.period_month, '')} {invoice.period_year}"

            late_fee = Invoice(
                tenant_id=tenant_id,
                client_id=client.id,
                connection_id=invoice.connection_id,
                billing_group_id=group.id,
                invoice_type=InvoiceType.LATE_FEE,
                period_month=invoice.period_month,
                period_year=invoice.period_year,
                period_label=period_label,
                amount=fee_amount,
                amount_paid=0.0,
                currency="MXN",
                status=InvoiceStatus.PENDING,
                due_date=ref_date,  # Vence hoy mismo
                suspension_date=invoice.suspension_date,  # Misma fecha de suspensión
                payment_link=client.payment_link,
                notes=f"Recargo automático por no pagar a tiempo (${fee_amount})",
            )
            db.add(late_fee)
            fees_generated += 1

            # Marcar la factura original como OVERDUE
            invoice.status = InvoiceStatus.OVERDUE

            logger.info(
                f"Recargo ${fee_amount} generado: {client.first_name} {client.last_name} "
                f"(cliente {client.id}) - {period_label}"
            )

        except Exception as e:
            errors.append(f"Error cliente {client.id}: {str(e)}")

    await db.commit()

    logger.info(
        f"Recargos generados: {fees_generated}, prepago ignorados: {skipped_prepago}"
    )

    return {
        "date": ref_date.isoformat(),
        "late_fees_generated": fees_generated,
        "skipped_prepago": skipped_prepago,
        "errors": errors,
    }


# ================================================================
# PROCESAR PAGO (WEBHOOK TAPIPAY)
# ================================================================

async def process_tapipay_payment(db: AsyncSession, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Procesa notificación de pago de tapipay (webhook)."""
    external_client_id = webhook_data.get("externalClientId", "")
    operation_id = webhook_data.get("operationId", "")
    status = webhook_data.get("status", "")
    amount = webhook_data.get("amount", 0)

    logger.info(f"Webhook tapipay: {external_client_id}, status={status}, ${amount}")

    if status == "confirmed":
        return await _process_confirmed(db, external_client_id, amount, operation_id, webhook_data)
    elif status == "reversed":
        return await _process_reversed(db, operation_id, amount)
    elif status == "failed":
        return {"status": "ignored", "reason": "payment_failed"}
    return {"status": "ignored", "reason": f"unknown: {status}"}


async def _process_confirmed(db, ext_client_id, amount, operation_id, raw_data):
    """Procesa pago confirmado → registrar + reactivar si aplica."""
    result = await db.execute(
        select(Client).where(Client.tapipay_identifier == ext_client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        logger.error(f"Cliente no encontrado: {ext_client_id}")
        return {"status": "error", "reason": "client_not_found"}

    # Buscar factura pendiente más antigua
    result = await db.execute(
        select(Invoice).where(
            Invoice.client_id == client.id,
            Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE,
                               InvoiceStatus.PARTIAL, InvoiceStatus.SUSPENDED]),
            Invoice.is_active == True
        ).order_by(Invoice.due_date.asc())
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        logger.warning(f"Sin factura pendiente para cliente {client.id}")
        return {"status": "warning", "reason": "no_pending_invoice"}

    # No duplicar pagos
    existing = await db.execute(
        select(Payment).where(Payment.tapipay_operation_id == operation_id)
    )
    if existing.scalar_one_or_none():
        return {"status": "ignored", "reason": "duplicate"}

    # Registrar pago
    payment = Payment(
        tenant_id=client.tenant_id, invoice_id=invoice.id, client_id=client.id,
        amount=amount, payment_method=PaymentMethod.OTHER,
        status=PaymentStatus.CONFIRMED, tapipay_operation_id=operation_id,
        tapipay_external_payment_id=raw_data.get("externalPaymentId"),
        tapipay_company_code=raw_data.get("companyCode"),
        tapipay_type=raw_data.get("type"),
        tapipay_additional_data=raw_data.get("additionalData"),
        paid_at=datetime.utcnow(), is_manual=False,
    )
    db.add(payment)

    # Actualizar factura
    invoice.amount_paid = (invoice.amount_paid or 0) + amount
    invoice.status = InvoiceStatus.PAID if invoice.amount_paid >= invoice.amount else InvoiceStatus.PARTIAL

    # REACTIVAR si pagó completo
    mk_result = None
    if invoice.status == InvoiceStatus.PAID:
        mk_result = await _reactivate_if_suspended(db, client)

    await db.commit()
    logger.info(f"Pago: cliente {client.id}, factura {invoice.id}, ${amount}, {invoice.status.value}")
    return {"status": "processed", "client_id": client.id, "invoice_id": invoice.id,
            "invoice_status": invoice.status.value, "reactivated": mk_result is not None}


async def _process_reversed(db, operation_id, amount):
    """Procesa reversión de pago."""
    result = await db.execute(
        select(Payment).where(Payment.tapipay_operation_id == operation_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return {"status": "warning", "reason": "payment_not_found"}

    payment.status = PaymentStatus.REVERSED
    invoice = await db.get(Invoice, payment.invoice_id)
    if invoice:
        invoice.amount_paid = max(0, (invoice.amount_paid or 0) - amount)
        if invoice.amount_paid < invoice.amount:
            invoice.status = InvoiceStatus.PENDING
    await db.commit()
    return {"status": "reversed", "invoice_id": invoice.id if invoice else None}


async def _reactivate_if_suspended(db, client):
    """Reactiva conexiones suspendidas del cliente en MikroTik."""
    result = await db.execute(
        select(Connection).where(
            Connection.client_id == client.id,
            Connection.status == ConnectionStatus.SUSPENDED,
            Connection.is_active == True
        )
    )
    connections = result.scalars().all()
    if not connections:
        return None

    results = []
    for conn in connections:
        try:
            mk = await reactivate_connection_mikrotik(db, conn)
            conn.status = ConnectionStatus.ACTIVE
            results.append({"connection_id": conn.id, "mikrotik": mk})
            logger.info(f"Auto-reactivado: cliente {client.id}, conexión {conn.id}")
        except Exception as e:
            results.append({"connection_id": conn.id, "error": str(e)})
    return results


# ================================================================
# SUSPENDER MOROSOS (AMBOS TIPOS)
# ================================================================

async def suspend_overdue_clients(db: AsyncSession, tenant_id: int, ref_date: Optional[date] = None):
    """
    Suspende clientes con facturas vencidas (ejecutar diario).
    Aplica tanto para CON_PLAN como PREPAGO.
    """
    if not ref_date:
        ref_date = date.today()

    result = await db.execute(
        select(Invoice, Connection, Client)
        .join(Connection, Invoice.connection_id == Connection.id)
        .join(Client, Invoice.client_id == Client.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE]),
            Invoice.suspension_date <= ref_date,
            Invoice.is_active == True,
            Connection.status == ConnectionStatus.ACTIVE,
            Connection.is_active == True
        )
    )
    rows = result.all()

    count = 0
    errors = []
    for invoice, connection, client in rows:
        try:
            await suspend_connection_mikrotik(db, connection)
            connection.status = ConnectionStatus.SUSPENDED
            invoice.status = InvoiceStatus.SUSPENDED
            count += 1
            logger.info(f"Suspendido: {client.first_name} {client.last_name} ({client.client_type.value})")
        except Exception as e:
            errors.append(f"Cliente {client.id}: {e}")

    await db.commit()
    return {"date": ref_date.isoformat(), "suspended": count, "errors": errors}


# ================================================================
# INFO FACTURACIÓN CLIENTE
# ================================================================

async def get_client_billing_info(db: AsyncSession, client_id: int, tenant_id: int):
    client = await db.get(Client, client_id)
    if not client or client.tenant_id != tenant_id:
        return {"error": "Cliente no encontrado"}

    group_name, cutoff_day = None, None
    if client.billing_group_id:
        group = await db.get(BillingGroup, client.billing_group_id)
        if group:
            group_name, cutoff_day = group.name, group.cutoff_day

    result = await db.execute(
        select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount - Invoice.amount_paid), 0))
        .where(Invoice.client_id == client_id,
               Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE,
                                   InvoiceStatus.PARTIAL, InvoiceStatus.SUSPENDED]),
               Invoice.is_active == True)
    )
    row = result.one()

    result2 = await db.execute(
        select(Payment.paid_at).where(
            Payment.client_id == client_id, Payment.status == PaymentStatus.CONFIRMED
        ).order_by(Payment.paid_at.desc()).limit(1)
    )

    return {
        "client_id": client.id,
        "client_name": f"{client.first_name} {client.last_name}",
        "tapipay_identifier": client.tapipay_identifier,
        "payment_link": client.payment_link,
        "billing_group": group_name, "cutoff_day": cutoff_day,
        "pending_invoices": row[0], "total_debt": float(row[1]),
        "last_payment_date": result2.scalar_one_or_none(),
    }