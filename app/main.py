"""
Sistema ISP - Punto de entrada FastAPI
Plataforma SaaS Multi-Tenant para ISPs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import engine, Base
from app.middleware.tenant_resolver import TenantResolverMiddleware

# Routers
from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.prospects import router as prospects_router
from app.routers.cells import router as cells_router
from app.routers.connections import router as connections_router
from app.routers.plans import router as plans_router
from app.routers.inventory import router as inventory_router
from app.routers.mikrotik import router as mikrotik_router
from app.routers.olt import router as olt_router
from app.routers.billing import router as billing_router
from app.routers.webhooks import router as webhooks_router
from app.routers.connection_diagnostics import router as diagnostics_router
from app.routers.client_files import router as client_files_router
from app.routers.tickets import router as tickets_router
from app.routers.whatsapp import router as whatsapp_router
from app.routers.whatsapp import webhook_router as whatsapp_webhook_router
from app.routers.payment_gateways import router as payment_gateways_router
from app.routers.payment_gateways import webhook_router as payment_webhook_router
from app.routers.mikrotik_import import router as mikrotik_import_router
from app.routers.dashboard import router as dashboard_router
from app.routers.localities import router as localities_router

# Importar modelos para que se registren
from app.models import *  # noqa

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas al iniciar (en desarrollo). En prod usar Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    yield
    await engine.dispose()
    print(f"👋 {settings.APP_NAME} detenido")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma SaaS para ISPs - Multi-Tenant",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantResolverMiddleware)




# Registrar routers
app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(prospects_router, prefix="/api/v1")
app.include_router(cells_router, prefix="/api/v1")
app.include_router(connections_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api")
app.include_router(mikrotik_router, prefix="/api/v1")
app.include_router(olt_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api")
app.include_router(diagnostics_router, prefix="/api")
app.include_router(client_files_router, prefix="/api")
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(whatsapp_router, prefix="/api")
app.include_router(whatsapp_webhook_router, prefix="/api")
app.include_router(payment_gateways_router, prefix="/api")
app.include_router(payment_webhook_router, prefix="/api")
app.include_router(mikrotik_import_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(localities_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }