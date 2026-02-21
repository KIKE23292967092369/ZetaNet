"""
NetKeeper - Router: Dashboard
Endpoint único que agrega todas las métricas para el dashboard del frontend.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from datetime import date
from dateutil.relativedelta import relativedelta

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.client import Client, ClientStatus
from app.models.prospect import Prospect, ProspectStatus
from app.models.connection import Connection, ConnectionStatus
from app.models.inventory import Onu, Cpe, Router
from app.models.billing import Invoice, Payment, InvoiceStatus, InvoiceType, PaymentStatus
from app.models.ticket import Ticket, TicketStatus, TicketType

router = APIRouter(prefix="/v1/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Retorna todas las métricas del dashboard en una sola llamada.
    """
    tid = user.tenant_id
    today = date.today()
    current_month = today.month
    current_year = today.year

    # Mes anterior
    prev = today - relativedelta(months=1)
    prev_month = prev.month
    prev_year = prev.year

    # ─── CLIENTES ───
    r = await db.execute(
        select(Client.status, func.count(Client.id))
        .where(Client.tenant_id == tid)
        .group_by(Client.status)
    )
    client_counts = dict(r.all())
    clientes_activos = client_counts.get(ClientStatus.ACTIVE, 0)
    clientes_suspendidos = client_counts.get(ClientStatus.SUSPENDED, 0)

    # Clientes nuevos este mes
    r = await db.execute(
        select(func.count(Client.id))
        .where(
            Client.tenant_id == tid,
            extract("month", Client.created_at) == current_month,
            extract("year", Client.created_at) == current_year,
        )
    )
    clientes_mes_actual = r.scalar() or 0

    # Clientes nuevos mes anterior
    r = await db.execute(
        select(func.count(Client.id))
        .where(
            Client.tenant_id == tid,
            extract("month", Client.created_at) == prev_month,
            extract("year", Client.created_at) == prev_year,
        )
    )
    clientes_mes_anterior = r.scalar() or 0

    # ─── CONEXIONES ───
    r = await db.execute(
        select(func.count(Connection.id))
        .where(Connection.tenant_id == tid, Connection.status == ConnectionStatus.ACTIVE)
    )
    conexiones_activas = r.scalar() or 0

    # Instalaciones (conexiones creadas) este mes
    r = await db.execute(
        select(func.count(Connection.id))
        .where(
            Connection.tenant_id == tid,
            extract("month", Connection.created_at) == current_month,
            extract("year", Connection.created_at) == current_year,
        )
    )
    instalaciones_mes_actual = r.scalar() or 0

    # Instalaciones mes anterior
    r = await db.execute(
        select(func.count(Connection.id))
        .where(
            Connection.tenant_id == tid,
            extract("month", Connection.created_at) == prev_month,
            extract("year", Connection.created_at) == prev_year,
        )
    )
    instalaciones_mes_anterior = r.scalar() or 0

    # ─── TICKETS ───
    pending_statuses = [TicketStatus.ABIERTO, TicketStatus.EN_PROCESO]

    # Tickets pendientes por tipo
    r = await db.execute(
        select(Ticket.ticket_type, func.count(Ticket.id))
        .where(
            Ticket.tenant_id == tid,
            Ticket.status.in_(pending_statuses),
        )
        .group_by(Ticket.ticket_type)
    )
    ticket_counts = dict(r.all())
    # Tu modelo tiene: INSTALACION, EVENTO, COBRANZA, OTRO (no hay SOPORTE)
    tickets_instalacion = ticket_counts.get(TicketType.INSTALACION, 0)
    tickets_evento = ticket_counts.get(TicketType.EVENTO, 0)
    tickets_cobranza = ticket_counts.get(TicketType.COBRANZA, 0)
    tickets_otro = ticket_counts.get(TicketType.OTRO, 0)

    # Promedio resolución instalación (tickets cerrados)
    r = await db.execute(
        select(
            func.avg(
                extract("epoch", Ticket.closed_at) - extract("epoch", Ticket.created_at)
            )
        )
        .where(
            Ticket.tenant_id == tid,
            Ticket.ticket_type == TicketType.INSTALACION,
            Ticket.status.in_([TicketStatus.RESUELTO, TicketStatus.CERRADO]),
            Ticket.closed_at.isnot(None),
        )
    )
    avg_instalacion_seconds = r.scalar()
    resolucion_instalacion_dias = round(avg_instalacion_seconds / 86400, 1) if avg_instalacion_seconds else 0

    # Promedio resolución otros tickets (evento + cobranza + otro)
    r = await db.execute(
        select(
            func.avg(
                extract("epoch", Ticket.closed_at) - extract("epoch", Ticket.created_at)
            )
        )
        .where(
            Ticket.tenant_id == tid,
            Ticket.ticket_type.in_([TicketType.EVENTO, TicketType.COBRANZA, TicketType.OTRO]),
            Ticket.status.in_([TicketStatus.RESUELTO, TicketStatus.CERRADO]),
            Ticket.closed_at.isnot(None),
        )
    )
    avg_otros_seconds = r.scalar()
    resolucion_otros_dias = round(avg_otros_seconds / 86400, 1) if avg_otros_seconds else 0

    # ─── INVENTARIO (disponible = is_active AND sin conexión) ───
    r = await db.execute(
        select(func.count(Onu.id))
        .where(Onu.tenant_id == tid, Onu.is_active == True, Onu.connection_id.is_(None))
    )
    onus_disponibles = r.scalar() or 0

    r = await db.execute(
        select(func.count(Cpe.id))
        .where(Cpe.tenant_id == tid, Cpe.is_active == True, Cpe.connection_id.is_(None))
    )
    cpes_disponibles = r.scalar() or 0

    r = await db.execute(
        select(func.count(Router.id))
        .where(Router.tenant_id == tid, Router.is_active == True, Router.connection_id.is_(None))
    )
    routers_disponibles = r.scalar() or 0

    # ─── PROSPECTOS (en seguimiento) ───
    r = await db.execute(
        select(func.count(Prospect.id))
        .where(
            Prospect.tenant_id == tid,
            Prospect.status.in_([
                ProspectStatus.PENDING,
                ProspectStatus.CONTACTED,
                ProspectStatus.INTERESTED,
            ]),
        )
    )
    prospectos_seguimiento = r.scalar() or 0

    # ─── FACTURACIÓN ───
    r = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tid,
            Invoice.period_month == current_month,
            Invoice.period_year == current_year,
            Payment.status == PaymentStatus.CONFIRMED,
        )
    )
    ingresos_mes = float(r.scalar() or 0)

    # Morosos (facturas vencidas o suspendidas)
    r = await db.execute(
        select(func.count(func.distinct(Invoice.client_id)))
        .where(
            Invoice.tenant_id == tid,
            Invoice.status.in_([InvoiceStatus.OVERDUE, InvoiceStatus.SUSPENDED]),
            Invoice.is_active == True,
        )
    )
    clientes_morosos = r.scalar() or 0

    # ─── NOMBRES DE MESES ───
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }

    return {
        # Info del periodo
        "current_month_name": meses.get(current_month, ""),
        "current_year": current_year,
        "prev_month_name": meses.get(prev_month, ""),
        "prev_year": prev_year,

        # Clientes
        "clientes_activos": clientes_activos,
        "clientes_suspendidos": clientes_suspendidos,
        "clientes_mes_actual": clientes_mes_actual,
        "clientes_mes_anterior": clientes_mes_anterior,

        # Conexiones
        "conexiones_activas": conexiones_activas,
        "instalaciones_mes_actual": instalaciones_mes_actual,
        "instalaciones_mes_anterior": instalaciones_mes_anterior,

        # Tickets (sin SOPORTE en tu modelo)
        "tickets_instalacion_pendientes": tickets_instalacion,
        "tickets_evento_pendientes": tickets_evento,
        "tickets_cobranza_pendientes": tickets_cobranza,
        "tickets_otro_pendientes": tickets_otro,
        "resolucion_instalacion_dias": resolucion_instalacion_dias,
        "resolucion_otros_dias": resolucion_otros_dias,

        # Inventario
        "onus_disponibles": onus_disponibles,
        "cpes_disponibles": cpes_disponibles,
        "routers_disponibles": routers_disponibles,

        # Prospectos
        "prospectos_seguimiento": prospectos_seguimiento,

        # Finanzas
        "ingresos_mes": ingresos_mes,
        "clientes_morosos": clientes_morosos,

        # WhatsApp (pendiente)
        "mensajes_sin_leer": 0,
    }