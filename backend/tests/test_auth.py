"""Auth, tenancy, RBAC, and Google SSO — functional + negative coverage."""
from __future__ import annotations

from app.models.identity import Role
from tests.conftest import bearer


# ---------- password login ----------

async def test_login_success(make_client, seeded):
    maker = seeded["maker"]
    async with make_client(maker) as c:
        resp = await c.post("/api/auth/login", json={"email": "super@x.com", "password": "Secret123!"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]


async def test_login_wrong_password_401(make_client, seeded):
    maker = seeded["maker"]
    async with make_client(maker) as c:
        resp = await c.post("/api/auth/login", json={"email": "super@x.com", "password": "nope"})
    assert resp.status_code == 401


async def test_login_unknown_email_401(make_client, db):
    async with make_client(db) as c:
        resp = await c.post("/api/auth/login", json={"email": "ghost@x.com", "password": "x"})
    assert resp.status_code == 401


# ---------- me / token handling ----------

async def test_me_returns_current_user(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["sa"], Role.SUPER_ADMIN, None)
    async with make_client(maker, auth) as c:
        resp = await c.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "super@x.com"
    assert resp.json()["role"] == "super_admin"


async def test_me_without_token_401(make_client, seeded):
    maker = seeded["maker"]
    async with make_client(maker) as c:
        resp = await c.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_invalid_token_401(make_client, seeded):
    maker = seeded["maker"]
    async with make_client(maker, "Bearer not.a.jwt") as c:
        resp = await c.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_token_for_deleted_user_401(make_client, seeded):
    maker = seeded["maker"]
    auth = bearer("doesnotexist", Role.USER, None)
    async with make_client(maker, auth) as c:
        resp = await c.get("/api/auth/me")
    assert resp.status_code == 401


# ---------- auth config ----------

async def test_auth_config_google_disabled(make_client, db):
    async with make_client(db) as c:
        resp = await c.get("/api/auth/config")
    assert resp.status_code == 200
    assert resp.json()["google_enabled"] is False


# ---------- tenant creation (super-admin only) ----------

async def test_super_admin_creates_tenant(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["sa"], Role.SUPER_ADMIN, None)
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/tenants", json={"name": "New Org", "slug": "new-org"})
    assert resp.status_code == 201
    assert resp.json()["slug"] == "new-org"


async def test_tenant_admin_cannot_create_tenant_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/tenants", json={"name": "X", "slug": "x"})
    assert resp.status_code == 403


async def test_duplicate_tenant_slug_409(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["sa"], Role.SUPER_ADMIN, None)
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/tenants", json={"name": "Dup", "slug": "react-org"})
    assert resp.status_code == 409


# ---------- user management + scope ----------

async def test_super_admin_lists_all_users(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["sa"], Role.SUPER_ADMIN, None)
    async with make_client(maker, auth) as c:
        resp = await c.get("/api/auth/users")
    assert resp.status_code == 200
    assert len(resp.json()) == 4


async def test_tenant_admin_lists_only_own_tenant(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])
    async with make_client(maker, auth) as c:
        resp = await c.get("/api/auth/users")
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert emails == {"a1@x.com", "u1@x.com"}


async def test_user_cannot_list_users_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["u1"], Role.USER, ids["t1"])
    async with make_client(maker, auth) as c:
        resp = await c.get("/api/auth/users")
    assert resp.status_code == 403


async def test_super_admin_creates_user_in_any_tenant(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["sa"], Role.SUPER_ADMIN, None)
    body = {"email": "new@x.com", "password": "password1", "role": "user", "tenant_id": ids["t2"]}
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/users", json=body)
    assert resp.status_code == 201
    assert resp.json()["tenant_id"] == ids["t2"]


async def test_tenant_admin_creates_user_forced_into_own_tenant(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])
    # Attempt to plant the user in t2 — must be overridden to t1.
    body = {"email": "planted@x.com", "password": "password1", "role": "user", "tenant_id": ids["t2"]}
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/users", json=body)
    assert resp.status_code == 201
    assert resp.json()["tenant_id"] == ids["t1"]


async def test_tenant_admin_cannot_create_super_admin_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])
    body = {"email": "evil@x.com", "password": "password1", "role": "super_admin"}
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/users", json=body)
    assert resp.status_code == 403


async def test_user_cannot_create_user_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["u1"], Role.USER, ids["t1"])
    body = {"email": "x@x.com", "password": "password1", "role": "user"}
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/users", json=body)
    assert resp.status_code == 403


async def test_duplicate_user_email_409(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    auth = bearer(ids["sa"], Role.SUPER_ADMIN, None)
    body = {"email": "u1@x.com", "password": "password1", "role": "user", "tenant_id": ids["t1"]}
    async with make_client(maker, auth) as c:
        resp = await c.post("/api/auth/users", json=body)
    assert resp.status_code == 409
