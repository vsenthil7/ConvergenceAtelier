"""Timezone-aware base + config coverage."""
from __future__ import annotations

from datetime import timezone

from app.config import Settings
from app.db.base import AwareDateTime, utcnow


def test_utcnow_is_aware():
    """Functional: utcnow returns a timezone-aware UTC datetime."""
    now = utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset() == timezone.utc.utcoffset(now)


def test_aware_datetime_has_timezone():
    """Functional: the shared column type enforces timezone storage."""
    assert AwareDateTime.timezone is True


def test_cors_origin_list_parsing():
    """Functional + negative: parse origins, ignoring blanks/whitespace."""
    s = Settings(cors_origins="http://a.com, http://b.com ,, ")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_cors_origin_list_empty():
    """Negative: empty origins yields empty list, never crashes."""
    s = Settings(cors_origins="")
    assert s.cors_origin_list == []


def test_use_mocks_default_true():
    """Functional: demo mode is the safe default (no external keys)."""
    assert Settings().use_mocks is True
