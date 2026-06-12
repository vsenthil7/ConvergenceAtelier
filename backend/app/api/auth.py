"""Authentication + tenant + user-management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user, require_roles, verify_google_id_token
from app.db.session import get_session
from app.models.identity import Role, User
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    PublicRegister,
    TenantCreate,
    TenantRead,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session, google_verifier=verify_google_id_token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, svc: AuthService = Depends(_service)) -> TokenResponse:
    token = await svc.authenticate(payload.email, payload.password)
    return TokenResponse(access_token=token)


@router.post("/google", response_model=TokenResponse)
async def login_google(
    payload: GoogleLoginRequest, svc: AuthService = Depends(_service)
) -> TokenResponse:
    token = await svc.login_google(payload.id_token)
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: PublicRegister, svc: AuthService = Depends(_service)
) -> TokenResponse:
    """Public self-service signup. Always creates a plain attendee (USER)."""
    token = await svc.register_public(payload)
    return TokenResponse(access_token=token)


@router.get("/config")
async def auth_config() -> dict[str, object]:
    """Public: tells the frontend whether to show the Google button."""
    return {
        "google_enabled": settings.google_oauth_enabled,
        "google_client_id": settings.google_client_id,
    }


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.post(
    "/tenants",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.SUPER_ADMIN))],
)
async def create_tenant(
    payload: TenantCreate, svc: AuthService = Depends(_service)
) -> TenantRead:
    return TenantRead.model_validate(await svc.register_tenant(payload))


@router.get("/users", response_model=list[UserRead])
async def list_users(
    actor: User = Depends(get_current_user), svc: AuthService = Depends(_service)
) -> list[UserRead]:
    return [UserRead.model_validate(u) for u in await svc.list_users_for(actor)]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    actor: User = Depends(get_current_user),
    svc: AuthService = Depends(_service),
) -> UserRead:
    return UserRead.model_validate(await svc.manage_user_create(actor, payload))
