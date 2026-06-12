"""Authentication + identity/tenant management service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.identity import Role, Tenant, User
from app.schemas.auth import TenantCreate, UserCreate
from app.services.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)

# Injectable verifier so tests don't hit Google. Returns the token's claims.
GoogleVerifier = Callable[[str], Awaitable[dict[str, Any]]]


class AuthService:
    def __init__(
        self, session: AsyncSession, google_verifier: GoogleVerifier | None = None
    ) -> None:
        self.session = session
        self._verify_google = google_verifier

    # ---------- token issuance ----------

    def _token_for(self, user: User) -> str:
        return create_access_token(
            subject=user.id,
            claims={"role": user.role.value, "tenant_id": user.tenant_id},
        )

    # ---------- registration ----------

    async def register_tenant(self, data: TenantCreate) -> Tenant:
        existing = await self.session.execute(
            select(Tenant).where(Tenant.slug == data.slug)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Tenant", data.slug)
        tenant = Tenant(name=data.name, slug=data.slug)
        self.session.add(tenant)
        await self.session.commit()
        await self.session.refresh(tenant)
        return tenant

    async def create_user(self, data: UserCreate) -> User:
        existing = await self.session.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("User", data.email)
        user = User(
            email=data.email,
            full_name=data.full_name,
            password_hash=hash_password(data.password),
            role=data.role,
            tenant_id=data.tenant_id,
            auth_provider="local",
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    # ---------- login ----------

    async def authenticate(self, email: str, password: str) -> str:
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        return self._token_for(user)

    async def login_google(self, id_token: str) -> str:
        if self._verify_google is None:
            raise UnauthorizedError("Google login is not configured")
        claims = await self._verify_google(id_token)
        email = claims.get("email")
        if not email:
            raise UnauthorizedError("Google token missing email")
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            # First Google login provisions a scoped USER with no tenant yet.
            user = User(
                email=email,
                full_name=claims.get("name", ""),
                password_hash="",
                role=Role.USER,
                tenant_id=None,
                auth_provider="google",
            )
            self.session.add(user)
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user)
        return self._token_for(user)

    # ---------- user management (scoped) ----------

    async def get_user(self, user_id: str) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User", user_id)
        return user

    async def list_users_for(self, actor: User) -> list[User]:
        stmt = select(User).order_by(User.email)
        if actor.role is Role.TENANT_ADMIN:
            stmt = stmt.where(User.tenant_id == actor.tenant_id)
        elif actor.role is not Role.SUPER_ADMIN:
            raise ForbiddenError("Only admins can list users")
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def manage_user_create(self, actor: User, data: UserCreate) -> User:
        """A tenant-admin may only create users inside their own tenant."""
        if actor.role is Role.TENANT_ADMIN:
            if data.role is Role.SUPER_ADMIN:
                raise ForbiddenError("Tenant admins cannot create super-admins")
            data = data.model_copy(update={"tenant_id": actor.tenant_id})
        elif actor.role is not Role.SUPER_ADMIN:
            raise ForbiddenError("Only admins can create users")
        return await self.create_user(data)
