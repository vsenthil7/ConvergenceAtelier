"""Google SSO + security primitives — functional and negative."""
from __future__ import annotations

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.identity import Role, User
from app.services.auth_service import AuthService
from app.services.errors import UnauthorizedError


# ---------- security primitives ----------

def test_password_round_trip():
    h = hash_password("hunter2")
    assert verify_password("hunter2", h) is True
    assert verify_password("wrong", h) is False


def test_verify_empty_hash_is_false():
    assert verify_password("anything", "") is False


def test_long_password_is_supported():
    # >72 bytes must not raise; pre-hash path keeps bcrypt happy.
    long = "p" * 200
    h = hash_password(long)
    assert verify_password(long, h) is True
    assert verify_password("p" * 199, h) is False


def test_verify_malformed_hash_is_false():
    # A non-bcrypt hash string triggers bcrypt's ValueError -> handled as False.
    assert verify_password("x", "not-a-bcrypt-hash") is False


def test_token_round_trip():
    token = create_access_token("user1", {"role": "user", "tenant_id": None})
    claims = decode_access_token(token)
    assert claims["sub"] == "user1"
    assert claims["role"] == "user"


def test_decode_invalid_token_raises():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("garbage")


# ---------- Google SSO via AuthService ----------

async def test_google_login_not_configured(db):
    maker = db
    async with maker() as s:
        svc = AuthService(s, google_verifier=None)
        with pytest.raises(UnauthorizedError):
            await svc.login_google("tok")


async def test_google_login_missing_email(db):
    maker = db

    async def verifier(_: str):
        return {"name": "No Email"}

    async with maker() as s:
        svc = AuthService(s, google_verifier=verifier)
        with pytest.raises(UnauthorizedError):
            await svc.login_google("tok")


async def test_google_login_provisions_new_user(db):
    maker = db

    async def verifier(_: str):
        return {"email": "newsso@x.com", "name": "SSO User"}

    async with maker() as s:
        svc = AuthService(s, google_verifier=verifier)
        token = await svc.login_google("tok")
        assert token
    # second login reuses the same user (no duplicate)
    async with maker() as s:
        svc = AuthService(s, google_verifier=verifier)
        token2 = await svc.login_google("tok")
        assert token2
        from sqlalchemy import func, select

        count = await s.scalar(select(func.count()).select_from(User).where(User.email == "newsso@x.com"))
        assert count == 1


async def test_list_users_forbidden_for_plain_user(db):
    maker = db
    async with maker() as s:
        svc = AuthService(s)
        plain = User(email="p@x.com", role=Role.USER, tenant_id="t")
        with pytest.raises(Exception):
            await svc.list_users_for(plain)
