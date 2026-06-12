"""Coverage for auth dependencies: current-user resolution + Google verifier."""
from __future__ import annotations

import httpx
import pytest

import app.core.deps as deps
from app.core.deps import assert_tenant_access, verify_google_id_token
from app.config import settings
from app.models.identity import Role, User
from app.services.errors import ForbiddenError, UnauthorizedError


# ---------- tenant access guard ----------

def test_super_admin_accesses_any_tenant():
    u = User(email="s@x.com", role=Role.SUPER_ADMIN, tenant_id=None)
    assert_tenant_access(u, "any-tenant")  # no raise


def test_user_accesses_own_tenant():
    u = User(email="u@x.com", role=Role.USER, tenant_id="t1")
    assert_tenant_access(u, "t1")  # no raise


def test_user_denied_other_tenant():
    u = User(email="u@x.com", role=Role.USER, tenant_id="t1")
    with pytest.raises(ForbiddenError):
        assert_tenant_access(u, "t2")


# ---------- Google tokeninfo verification (httpx mocked) ----------

def _mock_async_client(resp_status: int, payload: dict):
    class _Resp:
        status_code = resp_status

        def json(self):
            return payload

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return _Resp()

    return _Client


async def test_verify_google_ok(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")  # skip audience check
    monkeypatch.setattr(httpx, "AsyncClient", _mock_async_client(200, {"email": "g@x.com"}))
    data = await verify_google_id_token("tok")
    assert data["email"] == "g@x.com"


async def test_verify_google_bad_status(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _mock_async_client(400, {}))
    with pytest.raises(UnauthorizedError):
        await verify_google_id_token("tok")


async def test_verify_google_audience_mismatch(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "expected-aud")
    monkeypatch.setattr(httpx, "AsyncClient", _mock_async_client(200, {"email": "g@x.com", "aud": "other"}))
    with pytest.raises(UnauthorizedError):
        await verify_google_id_token("tok")


# ---------- get_current_user edge: token without subject ----------

async def test_current_user_token_missing_subject(make_client, seeded):
    import jwt as _jwt
    from app.config import settings as _settings

    # A validly-signed token that carries no "sub" claim.
    token = _jwt.encode({"role": "user"}, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)
    async with make_client(seeded["maker"], f"Bearer {token}") as c:
        resp = await c.get("/api/auth/me")
    assert resp.status_code == 401


# ---------- get_current_user resolved directly (deterministic coverage) ----------

async def test_get_current_user_resolves_and_missing(db):
    from fastapi.security import HTTPAuthorizationCredentials
    from app.core.deps import get_current_user
    from app.core.security import create_access_token
    from app.models.identity import Role, User

    maker = db
    async with maker() as s:
        u = User(email="who@x.com", role=Role.USER, tenant_id=None)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        uid = u.id

    # Valid token -> returns the user.
    async with maker() as s:
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=create_access_token(uid, {"role": "user", "tenant_id": None}),
        )
        resolved = await get_current_user(creds=creds, session=s)
        assert resolved.email == "who@x.com"

    # Token for a non-existent user -> Unauthorized.
    async with maker() as s:
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=create_access_token("missing", {"role": "user", "tenant_id": None}),
        )
        with pytest.raises(UnauthorizedError):
            await get_current_user(creds=creds, session=s)

    # No credentials at all -> Unauthorized.
    async with maker() as s:
        with pytest.raises(UnauthorizedError):
            await get_current_user(creds=None, session=s)
