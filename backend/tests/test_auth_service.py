"""Direct AuthService tests — deterministic coverage of service-layer branches
without going through the ASGI transport (which traces unreliably under load).
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.identity import Role, User
from app.schemas.auth import PublicRegister, TenantCreate, UserCreate
from app.services.auth_service import AuthService
from app.services.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_register_tenant_and_conflict(session):
    svc = AuthService(session)
    tenant = await svc.register_tenant(TenantCreate(name="Org", slug="org"))
    assert tenant.slug == "org"
    with pytest.raises(ConflictError):
        await svc.register_tenant(TenantCreate(name="Dup", slug="org"))


async def test_create_user_and_conflict(session):
    svc = AuthService(session)
    user = await svc.create_user(
        UserCreate(email="a@x.com", password="password1", role=Role.USER)
    )
    assert user.email == "a@x.com"
    assert user.auth_provider == "local"
    with pytest.raises(ConflictError):
        await svc.create_user(
            UserCreate(email="a@x.com", password="password1", role=Role.USER)
        )


async def test_authenticate_success_and_failures(session):
    svc = AuthService(session)
    await svc.create_user(
        UserCreate(email="a@x.com", password="password1", role=Role.USER)
    )
    token = await svc.authenticate("a@x.com", "password1")
    assert token
    with pytest.raises(UnauthorizedError):
        await svc.authenticate("a@x.com", "wrong")
    with pytest.raises(UnauthorizedError):
        await svc.authenticate("ghost@x.com", "password1")


async def test_list_users_for_super_and_tenant_and_forbidden(session):
    svc = AuthService(session)
    t = await svc.register_tenant(TenantCreate(name="Org", slug="org"))
    await svc.create_user(
        UserCreate(email="u@x.com", password="password1", role=Role.USER, tenant_id=t.id)
    )
    super_admin = User(email="s@x.com", role=Role.SUPER_ADMIN, tenant_id=None)
    tenant_admin = User(email="ta@x.com", role=Role.TENANT_ADMIN, tenant_id=t.id)
    plain = User(email="p@x.com", role=Role.USER, tenant_id=t.id)

    assert len(await svc.list_users_for(super_admin)) >= 1
    assert all(u.tenant_id == t.id for u in await svc.list_users_for(tenant_admin))
    with pytest.raises(ForbiddenError):
        await svc.list_users_for(plain)


async def test_manage_user_create_branches(session):
    svc = AuthService(session)
    t = await svc.register_tenant(TenantCreate(name="Org", slug="org"))
    super_admin = User(email="s@x.com", role=Role.SUPER_ADMIN, tenant_id=None)
    tenant_admin = User(email="ta@x.com", role=Role.TENANT_ADMIN, tenant_id=t.id)
    plain = User(email="p@x.com", role=Role.USER, tenant_id=t.id)

    # Super-admin can place a user in any tenant.
    created = await svc.manage_user_create(
        super_admin,
        UserCreate(email="new1@x.com", password="password1", role=Role.USER, tenant_id=t.id),
    )
    assert created.tenant_id == t.id

    # Tenant-admin is forced into own tenant.
    forced = await svc.manage_user_create(
        tenant_admin,
        UserCreate(email="new2@x.com", password="password1", role=Role.USER, tenant_id="other"),
    )
    assert forced.tenant_id == t.id

    # Tenant-admin cannot create a super-admin.
    with pytest.raises(ForbiddenError):
        await svc.manage_user_create(
            tenant_admin,
            UserCreate(email="evil@x.com", password="password1", role=Role.SUPER_ADMIN),
        )

    # Plain user cannot create users at all.
    with pytest.raises(ForbiddenError):
        await svc.manage_user_create(
            plain, UserCreate(email="x@x.com", password="password1", role=Role.USER)
        )


async def test_login_google_not_configured_and_provision(session):
    # Not configured -> raises.
    svc = AuthService(session, google_verifier=None)
    with pytest.raises(UnauthorizedError):
        await svc.login_google("tok")

    # Missing email -> raises.
    async def no_email(_):
        return {"name": "x"}

    svc2 = AuthService(session, google_verifier=no_email)
    with pytest.raises(UnauthorizedError):
        await svc2.login_google("tok")

    # Provisions a new user, second call reuses it.
    async def good(_):
        return {"email": "g@x.com", "name": "G"}

    svc3 = AuthService(session, google_verifier=good)
    assert await svc3.login_google("tok")
    assert await svc3.login_google("tok")


async def test_register_public_success_forces_user_role(session):
    svc = AuthService(session)
    t = await svc.register_tenant(TenantCreate(name="Org", slug="org"))
    token = await svc.register_public(
        PublicRegister(
            email="selfsignup@x.com",
            full_name="Self Signup",
            password="password1",
            tenant_slug="org",
        )
    )
    assert token
    # The created user is a plain USER in that tenant (never an admin).
    from sqlalchemy import select

    created = (
        await session.execute(select(User).where(User.email == "selfsignup@x.com"))
    ).scalar_one()
    assert created.role is Role.USER
    assert created.tenant_id == t.id
    assert created.last_login_at is not None


async def test_register_public_unknown_tenant_raises(session):
    svc = AuthService(session)
    with pytest.raises(NotFoundError):
        await svc.register_public(
            PublicRegister(
                email="x@x.com", password="password1", tenant_slug="missing"
            )
        )
