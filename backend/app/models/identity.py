"""Tenant + User models with role-based access (timezone-aware)."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AwareDateTime, Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class Role(str, enum.Enum):
    """Access tiers.

    SUPER_ADMIN  — platform owner; sees and manages ALL tenants.
    TENANT_ADMIN — manages users + data within their own tenant only.
    USER         — scoped read/participate access within their tenant.
    """

    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    USER = "user"


class Tenant(TimestampMixin, Base):
    """An organisation. All organiser data is isolated per tenant."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)

    users: Mapped[list["User"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class User(TimestampMixin, Base):
    """A person. Belongs to one tenant; super-admins span all tenants."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    # Hash is empty for SSO-only accounts.
    password_hash: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.USER, nullable=False)
    # Nullable for super-admins (not bound to a single tenant).
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(AwareDateTime, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(40), default="local", nullable=False)

    tenant: Mapped[Tenant | None] = relationship(back_populates="users")
