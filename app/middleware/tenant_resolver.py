"""
NetKeeper - Tenant Resolver Middleware
Extrae el subdominio de la petición y resuelve el tenant_id.

hfiber.netkeeper.com.mx → tenant_id = 1
wispredes.netkeeper.com.mx → tenant_id = 2
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant


# Rutas que NO requieren tenant (registro, landing, health)
PUBLIC_PATHS = [
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/register-tenant",
]


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """
    Middleware que resuelve el tenant a partir del subdominio.
    Inyecta tenant_id y tenant_slug en request.state.
    """

    def __init__(self, app, base_domain: str = "netkeeper.com.mx"):
        super().__init__(app)
        self.base_domain = base_domain

    async def dispatch(self, request: Request, call_next):
        # Saltar rutas públicas
        if any(request.url.path.startswith(path) for path in PUBLIC_PATHS):
            request.state.tenant_id = None
            request.state.tenant_slug = None
            return await call_next(request)

        # Extraer subdominio
        host = request.headers.get("host", "").split(":")[0]  # quitar puerto
        slug = self._extract_slug(host)

        # En desarrollo, también aceptar header X-Tenant-Slug
        if not slug:
            if host in ("localhost", "127.0.0.1"):
                request.state.tenant_id = None
                request.state.tenant_slug = None
                return await call_next(request)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo identificar el tenant. Usa un subdominio válido o el header X-Tenant-Slug.",
            )

        # Buscar tenant en BD
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
            )
            tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{slug}' no encontrado o inactivo.",
            )

        if tenant.status.value == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta cuenta está suspendida. Contacta soporte.",
            )

        # Inyectar tenant en el request
        request.state.tenant_id = tenant.id
        request.state.tenant_slug = tenant.slug
        request.state.tenant_plan = tenant.plan.value

        return await call_next(request)

    def _extract_slug(self, host: str) -> str | None:
        """
        Extrae slug del subdominio.
        hfiber.netkeeper.com.mx → "hfiber"
        localhost → None
        netkeeper.com.mx → None (es el dominio base)
        """
        if host in ("localhost", "127.0.0.1", self.base_domain):
            return None

        # Para desarrollo: hfiber.localhost
        if host.endswith(".localhost"):
            return host.replace(".localhost", "")

        # Para producción: hfiber.netkeeper.com.mx
        if host.endswith(f".{self.base_domain}"):
            return host.replace(f".{self.base_domain}", "")

        return None
