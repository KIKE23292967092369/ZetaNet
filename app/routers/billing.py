"""
Sistema ISP - Router: Facturación
Endpoints para grupos de corte, facturas, pagos, recargos, tapipay.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import date
import logging

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.client import Client
from app.models.billing import (
    BillingGroup, TapipayConfig, Invoice, Payment,
    InvoiceStatus, InvoiceType, PaymentStatus, PaymentMethod
)
from app.schemas.billing import (
    BillingGroupCreate, BillingGroupUpdate, BillingGroupResponse,
    TapipayConfigCreate, TapipayConfigUpdate, TapipayConfigResponse,
    InvoiceCreate, InvoiceResponse,
    GenerateBillingRequest, GenerateBillingResponse,
    PaymentManualCreate, PaymentResponse,
    AssignBillingGroupRequest, ClientBillingInfo,
    LateFeeResponse
)
from app.services.billing_service import (
    generate_invoices_for_group, get_client_billing_info,
    suspend_overdue_clients, generate_tapipay_identifier,
    get_tapipay_service, generate_late_fees
)
from app.services.tapipay_service import TapipayError

logger = logging.getLogger("billing_router")

router = APIRouter(prefix="/billing", tags=["Facturación"])


# ================================================================
# GRUPOS DE CORTE
# ================================================================

@router.post("/groups", status_code=201)
async def create_billing_group(
    data: BillingGroupCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Crear grupo de corte. Ejemplo: "Corte día 5" con cutoff_day=5"""
    group = BillingGroup(
        tenant_id=user.tenant_id,
        name=data.name,
        cutoff_day=data.cutoff_day,
        grace_days=data.grace_days,
        reconnection_fee=data.reconnection_fee,
        description=data.description,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return {"message": "Grupo creado", "id": group.id, "name": group.name,
            "cutoff_day": group.cutoff_day, "grace_days": group.grace_days,
            "reconnection_fee": group.reconnection_fee}


@router.get("/groups", response_model=List[BillingGroupResponse])
async def list_billing_groups(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Lista todos los grupos de corte con conteo de clientes."""
    result = await db.execute(
        select(BillingGroup, func.count(Client.id).label("client_count"))
        .outerjoin(Client, Client.billing_group_id == BillingGroup.id)
        .where(BillingGroup.tenant_id == user.tenant_id)
        .group_by(BillingGroup.id)
        .order_by(BillingGroup.cutoff_day)
    )
    rows = result.all()
    return [
        BillingGroupResponse(
            id=g.id, name=g.name, cutoff_day=g.cutoff_day,
            grace_days=g.grace_days, reconnection_fee=g.reconnection_fee,
            description=g.description, is_active=g.is_active, client_count=c
        )
        for g, c in rows
    ]


@router.patch("/groups/{group_id}")
async def update_billing_group(
    group_id: int, data: BillingGroupUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    group = await db.get(BillingGroup, group_id)
    if not group or group.tenant_id != user.tenant_id:
        raise HTTPException(404, "Grupo no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(group, k, v)
    await db.commit()
    return {"message": "Grupo actualizado"}


@router.delete("/groups/{group_id}")
async def delete_billing_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    group = await db.get(BillingGroup, group_id)
    if not group or group.tenant_id != user.tenant_id:
        raise HTTPException(404, "Grupo no encontrado")
    result = await db.execute(
        select(func.count(Client.id)).where(Client.billing_group_id == group_id)
    )
    if result.scalar() > 0:
        raise HTTPException(400, "No se puede eliminar: tiene clientes asignados")
    await db.delete(group)
    await db.commit()
    return {"message": "Grupo eliminado"}


# ================================================================
# ASIGNAR CLIENTES A GRUPO
# ================================================================

@router.post("/groups/assign-clients")
async def assign_clients_to_group(
    data: AssignBillingGroupRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Asignar clientes a un grupo. Auto-genera identifier y payment_link."""
    group = await db.get(BillingGroup, data.billing_group_id)
    if not group or group.tenant_id != user.tenant_id:
        raise HTTPException(404, "Grupo no encontrado")

    tapipay = None
    try:
        tapipay = await get_tapipay_service(db, user.tenant_id)
    except TapipayError:
        pass

    updated = 0
    for client_id in data.client_ids:
        client = await db.get(Client, client_id)
        if not client or client.tenant_id != user.tenant_id:
            continue
        client.billing_group_id = data.billing_group_id
        if not client.tapipay_identifier:
            client.tapipay_identifier = generate_tapipay_identifier(client.id)
        if not client.payment_link and tapipay:
            client.payment_link = tapipay.get_payment_link(client.tapipay_identifier)
        updated += 1

    await db.commit()
    return {"message": f"{updated} clientes asignados a '{group.name}'", "updated": updated}


# ================================================================
# CONFIGURACIÓN TAPIPAY
# ================================================================

@router.post("/tapipay-config", status_code=201)
async def create_tapipay_config(
    data: TapipayConfigCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(TapipayConfig).where(
            TapipayConfig.tenant_id == user.tenant_id,
            TapipayConfig.is_active == True
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Ya existe configuración tapipay activa. Use PATCH.")
    config = TapipayConfig(tenant_id=user.tenant_id, **data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return {"message": "Configuración tapipay creada", "id": config.id}


@router.get("/tapipay-config", response_model=TapipayConfigResponse)
async def get_tapipay_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(TapipayConfig).where(
            TapipayConfig.tenant_id == user.tenant_id,
            TapipayConfig.is_active == True
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "No hay configuración tapipay")
    return config


@router.patch("/tapipay-config/{config_id}")
async def update_tapipay_config(
    config_id: int, data: TapipayConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    config = await db.get(TapipayConfig, config_id)
    if not config or config.tenant_id != user.tenant_id:
        raise HTTPException(404, "Configuración no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(config, k, v)
    await db.commit()
    return {"message": "Configuración actualizada"}


@router.get("/tapipay-config/test")
async def test_tapipay_connection(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        service = await get_tapipay_service(db, user.tenant_id)
        result = await service.test_connection()
        return result
    except TapipayError as e:
        return {"connected": False, "error": str(e)}


# ================================================================
# GENERAR FACTURAS (PROCESO MENSUAL)
# ================================================================

@router.post("/generate", response_model=GenerateBillingResponse)
async def generate_billing(
    data: GenerateBillingRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Genera facturas mensuales para un grupo de corte.
    Crea una factura por cliente con el monto de su plan.
    """
    try:
        result = await generate_invoices_for_group(
            db, user.tenant_id, data.billing_group_id,
            data.period_month, data.period_year, data.sync_tapipay
        )
        return GenerateBillingResponse(**result)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ================================================================
# GENERAR RECARGOS (EJECUTAR DIARIO)
# ================================================================

@router.post("/generate-late-fees", response_model=LateFeeResponse)
async def generate_late_fees_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Genera recargos automáticos.
    - CON_PLAN: Si no pagó el día de corte → recargo de $50 (configurable)
    - PREPAGO: No se cobra recargo
    Ejecutar diariamente (manual o con cron).
    """
    result = await generate_late_fees(db, user.tenant_id)
    return LateFeeResponse(**result)


# ================================================================
# FACTURAS
# ================================================================

@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    client_id: Optional[int] = None,
    billing_group_id: Optional[int] = None,
    status: Optional[str] = None,
    invoice_type: Optional[str] = None,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Listar facturas con filtros. Puedes filtrar por invoice_type=late_fee para ver solo recargos."""
    q = select(Invoice).where(
        Invoice.tenant_id == user.tenant_id,
        Invoice.is_active == True
    )
    if client_id:
        q = q.where(Invoice.client_id == client_id)
    if billing_group_id:
        q = q.where(Invoice.billing_group_id == billing_group_id)
    if status:
        q = q.where(Invoice.status == status)
    if invoice_type:
        q = q.where(Invoice.invoice_type == invoice_type)
    if period_month:
        q = q.where(Invoice.period_month == period_month)
    if period_year:
        q = q.where(Invoice.period_year == period_year)

    q = q.order_by(Invoice.id.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    invoice = await db.get(Invoice, invoice_id)
    if not invoice or invoice.tenant_id != user.tenant_id:
        raise HTTPException(404, "Factura no encontrada")
    return invoice


@router.post("/invoices/manual", response_model=InvoiceResponse, status_code=201)
async def create_manual_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    client = await db.get(Client, data.client_id)
    if not client or client.tenant_id != user.tenant_id:
        raise HTTPException(404, "Cliente no encontrado")

    invoice = Invoice(
        tenant_id=user.tenant_id,
        client_id=data.client_id,
        connection_id=data.connection_id,
        invoice_type=InvoiceType.MANUAL,
        period_month=data.period_month,
        period_year=data.period_year,
        period_label=f"{data.period_month}/{data.period_year}",
        amount=data.amount,
        amount_paid=0.0,
        currency="MXN",
        status=InvoiceStatus.PENDING,
        due_date=data.due_date,
        notes=data.notes,
        payment_link=client.payment_link,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.delete("/invoices/{invoice_id}")
async def cancel_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    invoice = await db.get(Invoice, invoice_id)
    if not invoice or invoice.tenant_id != user.tenant_id:
        raise HTTPException(404, "Factura no encontrada")
    if invoice.amount_paid > 0:
        raise HTTPException(400, "No se puede cancelar: ya tiene pagos")
    invoice.status = InvoiceStatus.CANCELLED
    invoice.is_active = False
    await db.commit()
    return {"message": "Factura cancelada"}


# ================================================================
# PAGOS
# ================================================================

@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    client_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    q = select(Payment).where(
        Payment.tenant_id == user.tenant_id,
        Payment.is_active == True
    )
    if client_id:
        q = q.where(Payment.client_id == client_id)
    if invoice_id:
        q = q.where(Payment.invoice_id == invoice_id)
    q = q.order_by(Payment.id.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/payments/manual", response_model=PaymentResponse, status_code=201)
async def register_manual_payment(
    data: PaymentManualCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Registrar pago manual. Si queda pagada, reactiva automáticamente."""
    invoice = await db.get(Invoice, data.invoice_id)
    if not invoice or invoice.tenant_id != user.tenant_id:
        raise HTTPException(404, "Factura no encontrada")

    from app.services.billing_service import _reactivate_if_suspended

    payment = Payment(
        tenant_id=user.tenant_id,
        invoice_id=invoice.id,
        client_id=invoice.client_id,
        amount=data.amount,
        payment_method=PaymentMethod.MANUAL,
        status=PaymentStatus.CONFIRMED,
        is_manual=True,
        registered_by=user.id,
        notes=data.notes,
    )
    db.add(payment)

    invoice.amount_paid = (invoice.amount_paid or 0) + data.amount
    if invoice.amount_paid >= invoice.amount:
        invoice.status = InvoiceStatus.PAID
    else:
        invoice.status = InvoiceStatus.PARTIAL

    if invoice.status == InvoiceStatus.PAID:
        client = await db.get(Client, invoice.client_id)
        if client:
            await _reactivate_if_suspended(db, client)

    await db.commit()
    await db.refresh(payment)
    return payment


# ================================================================
# SUSPENDER MOROSOS
# ================================================================

@router.post("/suspend-overdue")
async def suspend_overdue(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Suspender morosos (CON_PLAN y PREPAGO). Ejecutar diariamente."""
    result = await suspend_overdue_clients(db, user.tenant_id)
    return result


# ================================================================
# INFO FACTURACIÓN DE UN CLIENTE
# ================================================================

@router.get("/client/{client_id}/info", response_model=ClientBillingInfo)
async def get_billing_info(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    info = await get_client_billing_info(db, client_id, user.tenant_id)
    if "error" in info:
        raise HTTPException(404, info["error"])
    return ClientBillingInfo(**info)


# ================================================================
# DASHBOARD
# ================================================================

@router.get("/dashboard")
async def billing_dashboard(
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    tid = user.tenant_id
    if not period_month:
        period_month = date.today().month
    if not period_year:
        period_year = date.today().year

    r1 = await db.execute(
        select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0))
        .where(Invoice.tenant_id == tid, Invoice.period_month == period_month,
               Invoice.period_year == period_year, Invoice.is_active == True)
    )
    total_invoices, total_billed = r1.one()

    r2 = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .where(Invoice.tenant_id == tid, Invoice.period_month == period_month,
               Invoice.period_year == period_year, Payment.status == PaymentStatus.CONFIRMED)
    )
    total_collected = r2.scalar()

    r3 = await db.execute(
        select(func.count(Invoice.id))
        .where(Invoice.tenant_id == tid, Invoice.period_month == period_month,
               Invoice.period_year == period_year,
               Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE, InvoiceStatus.PARTIAL]),
               Invoice.is_active == True)
    )
    pending_count = r3.scalar()

    r4 = await db.execute(
        select(func.count(Invoice.id))
        .where(Invoice.tenant_id == tid, Invoice.period_month == period_month,
               Invoice.period_year == period_year,
               Invoice.status == InvoiceStatus.SUSPENDED, Invoice.is_active == True)
    )
    suspended_count = r4.scalar()

    # Total recargos generados
    r5 = await db.execute(
        select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0))
        .where(Invoice.tenant_id == tid, Invoice.period_month == period_month,
               Invoice.period_year == period_year,
               Invoice.invoice_type == InvoiceType.LATE_FEE, Invoice.is_active == True)
    )
    late_fee_count, late_fee_total = r5.one()

    return {
        "period": f"{period_month}/{period_year}",
        "total_invoices": total_invoices,
        "total_billed": float(total_billed),
        "total_collected": float(total_collected),
        "collection_rate": round(float(total_collected) / float(total_billed) * 100, 1) if total_billed > 0 else 0,
        "pending_invoices": pending_count,
        "suspended_clients": suspended_count,
        "outstanding": float(total_billed) - float(total_collected),
        "late_fees_count": late_fee_count,
        "late_fees_total": float(late_fee_total),
    }