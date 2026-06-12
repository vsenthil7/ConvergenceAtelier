"""Password hashing + JWT token helpers.

Uses the bcrypt library directly (not passlib) — passlib 1.7.4's version probe is
incompatible with bcrypt 5.x. bcrypt's 72-byte input limit is handled by hashing
longer secrets through SHA-256 first so no input is ever rejected.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings


def _prepare(secret: str) -> bytes:
    """Return a bcrypt-safe (<=72 byte) representation of any-length secret."""
    raw = secret.encode("utf-8")
    if len(raw) > 72:
        # Pre-hash long inputs; base64 keeps it ASCII and within 72 bytes.
        raw = base64.b64encode(hashlib.sha256(raw).digest())
    return raw


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_prepare(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(subject: str, claims: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        **claims,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode + verify a token. Raises jwt.PyJWTError on any problem."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
