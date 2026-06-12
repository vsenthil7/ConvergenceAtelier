"""FastAPI auth dependencies: resolve current user, enforce roles + tenant scope."""
from __future__ import annotations

from typing import Any

import httpx
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.identity import Role, User
from app.services.errors import ForbiddenError, UnauthorizedError

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None:
        raise UnauthorizedError("Missing bearer token")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user


def require_roles(*roles: Role):
    """Dependency factory enforcing the user holds one of the given roles."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError("Insufficient role")
        return user

    return _checker


def assert_tenant_access(actor: User, tenant_id: str | None) -> None:
    """Super-admins may access any tenant; others only their own."""
    if actor.role is Role.SUPER_ADMIN:
        return
    if tenant_id is not None and actor.tenant_id == tenant_id:
        return
    raise ForbiddenError("Tenant access denied")


async def verify_google_id_token(id_token: str) -> dict[str, Any]:
    """Verify a Google ID token via Google's tokeninfo endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}
        )
    if resp.status_code != 200:
        raise UnauthorizedError("Invalid Google token")
    data = resp.json()
    if settings.google_client_id and data.get("aud") != settings.google_client_id:
        raise UnauthorizedError("Google token audience mismatch")
    return data
