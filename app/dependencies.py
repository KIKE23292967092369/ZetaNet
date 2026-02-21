"""
NetKeeper - Dependencies (FastAPI Depends)
Funciones que se inyectan en los endpoints para obtener
el usuario actual, el tenant, y validar permisos.
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.middleware.auth import decode_token
from app.models.user import User, UserRole

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extrae y valida el JWT del header Authorization.
    Verifica que el user pertenezca al tenant del request.
    """
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    user_id = int(payload["sub"])
    token_tenant_id = payload["tenant_id"]

    # Verificar que el tenant del token coincida con el del subdominio
    request_tenant_id = getattr(request.state, "tenant_id", None)
    if request_tenant_id and token_tenant_id != request_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tenant.",
        )

    # Buscar usuario
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == token_tenant_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
        )

    return user


def require_role(*roles: UserRole):
    """
    Dependency factory que verifica que el usuario tenga uno de los roles permitidos.

    Uso:
        @router.post("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(r.value for r in roles)}",
            )
        return current_user
    return role_checker


def get_tenant_id(request: Request) -> int:
    """Obtiene el tenant_id del request (inyectado por el middleware)."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant no identificado.",
        )
    return tenant_id
