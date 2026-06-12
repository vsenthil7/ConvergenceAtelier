"""Unit tests for the deterministic local embedding + cosine similarity."""
from __future__ import annotations

import math

import pytest

from app.core.embedding import EMBED_DIM, cosine, default_embedder, embed, tokenize


def test_tokenize_lowercases_and_drops_stopwords():
    toks = tokenize("How to Build the React App")
    assert "react" in toks and "build" in toks
    # stopwords removed
    assert "the" not in toks and "to" not in toks and "how" not in toks


def test_embed_is_unit_length_for_nonempty_text():
    vec = embed("machine learning at scale")
    assert len(vec) == EMBED_DIM
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, rel_tol=1e-9)


def test_embed_empty_text_is_zero_vector():
    vec = embed("the and of")  # all stopwords -> no tokens
    assert len(vec) == EMBED_DIM
    assert all(v == 0.0 for v in vec)


def test_embed_is_deterministic():
    assert embed("GraphQL federation") == embed("GraphQL federation")


def test_cosine_identical_text_is_one():
    a = embed("kubernetes operators in production")
    assert math.isclose(cosine(a, a), 1.0, rel_tol=1e-9)


def test_cosine_related_text_higher_than_unrelated():
    base = embed("react state management with hooks")
    related = embed("react hooks and component state")
    unrelated = embed("sourdough bread baking techniques")
    assert cosine(base, related) > cosine(base, unrelated)


def test_cosine_zero_vector_returns_zero():
    a = embed("the and of")  # zero vector
    b = embed("real topic words here")
    assert cosine(a, b) == 0.0


def test_cosine_length_mismatch_raises():
    with pytest.raises(ValueError):
        cosine([1.0, 0.0], [1.0, 0.0, 0.0])


def test_default_embedder_returns_embed():
    assert default_embedder() is embed
