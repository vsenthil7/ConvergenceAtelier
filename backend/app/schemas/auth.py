"""Auth + identity schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.identity import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class GoogleLoginRequest(BaseModel):
    # The Google ID token (JWT) obtained client-side; verified server-side.
    id_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(default="", max_length=200)
    password: str = Field(min_length=8, max_length=200)
    role: Role = Role.USER
    tenant_id: str | None = None


class PublicRegister(BaseModel):
    """Self-service signup. Always provisions a plain USER in a chosen tenant;
    the role is fixed server-side so a caller can never self-grant admin."""

    email: EmailStr
    full_name: str = Field(default="", max_length=200)
    password: str = Field(min_length=8, max_length=200)
    tenant_slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str
    role: Role
    tenant_id: str | None
    auth_provider: str
    last_login_at: datetime | None


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str
