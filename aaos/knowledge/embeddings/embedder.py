"""
Embedding providers.

Primary: OpenAI text-embedding-3-small (if OPENAI_API_KEY).
Fallback: local hashing embedder (no network, deterministic).
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class Embedder(Protocol):
    name: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_one(self, text: str) -> list[float]: ...


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    return re.findall(r"[\w\u0600-\u06FF]+", text, flags=re.UNICODE)


class LocalHashEmbedder:
    """
    Lightweight bag-of-tokens hashed into a fixed vector.
    Not as strong as neural embeddings, but enables offline semantic-ish search.
    """

    name = "local-hash"
    dimensions = 384

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def _vec(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimensions
            sign = 1.0 if (h // self.dimensions) % 2 == 0 else -1.0
            vec[idx] += sign
            # bigrams
        for a, b in zip(tokens, tokens[1:]):
            h = int(hashlib.md5(f"{a}_{b}".encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimensions
            sign = 1.0 if (h // self.dimensions) % 2 == 0 else -1.0
            vec[idx] += 0.5 * sign
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self._vec(text)


class OpenAIEmbedder:
    name = "openai"
    dimensions = 1536

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        from openai import OpenAI

        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY required for OpenAIEmbedder")
        self.client = OpenAI(api_key=key)
        self.model = model
        # text-embedding-3-small default dims 1536
        self.dimensions = 1536

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # API limit batch size; chunk requests
        out: list[list[float]] = []
        batch = 64
        for i in range(0, len(texts), batch):
            part = texts[i : i + batch]
            resp = self.client.embeddings.create(model=self.model, input=part)
            # ensure order by index
            data = sorted(resp.data, key=lambda d: d.index)
            out.extend([list(d.embedding) for d in data])
        return out

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


def get_embedder() -> Embedder:
    """Prefer OpenAI when key present; else local hash."""
    if os.getenv("OPENAI_API_KEY"):
        try:
            return OpenAIEmbedder()
        except Exception as e:
            logger.warning("OpenAI embedder unavailable (%s); using local", e)
    return LocalHashEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
