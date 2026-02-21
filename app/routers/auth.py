"""
NetKeeper - Router de Autenticación
Login, refresh token, registro de tenant.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.tenant import Tenant, TenantStatus, TenantPlan
from app.models.user import User, UserRole
from app.middleware.auth import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    TenantCreate,
    TenantResponse,
    UserCreate,
)
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autenticación por email + password. Retorna JWT."""
    result = await db.execute(
        select(User).where(User.email == data.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )

    access_token = create_access_token(user.id, user.tenant_id, user.role.value)
    refresh_token = create_refresh_token(user.id, user.tenant_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Renueva el access token usando un refresh token válido."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado.",
        )

    user_id = int(payload["sub"])
    tenant_id = payload["tenant_id"]

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")

    access_token = create_access_token(user.id, user.tenant_id, user.role.value)
    new_refresh = create_refresh_token(user.id, user.tenant_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/register-tenant", response_model=TenantResponse, status_code=201)
async def register_tenant(
    data: TenantCreate,
    admin_password: str = "admin123",  # En producción viene del body
    db: AsyncSession = Depends(get_db),
):
    """
    Registra un nuevo ISP (tenant) con su usuario admin.
    Este es el onboarding de nuevos ISPs.
    """
    # Verificar slug único
    existing = await db.execute(select(Tenant).where(Tenant.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El slug '{data.slug}' ya está en uso.",
        )

    # Crear tenant
    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        email=data.email,
        phone=data.phone,
        city=data.city,
        state=data.state,
        plan=TenantPlan.STARTER,
        status=TenantStatus.TRIAL,
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db.add(tenant)
    await db.flush()  # Para obtener el ID

    # Crear usuario admin del tenant
    admin_user = User(
        tenant_id=tenant.id,
        email=data.email,
        username=data.slug + "_admin",
        hashed_password=hash_password(admin_password),
        full_name=f"Admin {data.name}",
        role=UserRole.ADMIN,
    )
    db.add(admin_user)

    return TenantResponse.model_validate(tenant)
