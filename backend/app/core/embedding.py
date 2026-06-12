"""Lightweight semantic embedding + similarity for AI discovery (S3).

Demo mode needs zero external keys, so the default embedder is a deterministic,
dependency-free bag-of-words hashing vectoriser: tokenise text, hash each token
into a fixed-width vector, L2-normalise. Cosine similarity on these vectors gives
a stable, explainable "semantic" score that is identical across runs (important
for reproducible demos and tests).

For production, ``use_mocks=false`` + an API key lets a caller inject a real
embedding function with the same ``(str) -> list[float]`` signature; nothing else
in the recommendation/matchmaking layer changes.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable

# Width of the hashing vector. Small enough to be fast, wide enough that token
# collisions are rare for short conference-talk texts.
EMBED_DIM = 256

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common words carry no topical signal; dropping them sharpens similarity.
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
        "is", "are", "be", "how", "what", "your", "you", "we", "our", "this",
        "that", "from", "by", "at", "as", "it", "into", "via", "using", "use",
    }
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens with stopwords removed."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def _token_bucket(token: str) -> int:
    """Stable hash of a token into [0, EMBED_DIM)."""
    digest = hashlib.sha1(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % EMBED_DIM


def embed(text: str) -> list[float]:
    """Deterministic L2-normalised bag-of-words hashing embedding."""
    vec = [0.0] * EMBED_DIM
    for token in tokenize(text):
        vec[_token_bucket(token)] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors (0.0 when either is empty)."""
    if len(a) != len(b):
        raise ValueError("vectors must be the same length")
    dot = sum(x * y for x, y in zip(a, b))
    # Inputs are pre-normalised by ``embed`` so the dot product is the cosine,
    # but we guard against non-normalised injected embedders too.
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# An embedder is any function turning text into a vector. Default is the local one.
Embedder = Callable[[str], list[float]]


def default_embedder() -> Embedder:
    return embed
