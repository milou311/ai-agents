"""Chunk text and write embeddings into the vector store."""

from __future__ import annotations

import re
from typing import Optional

from aaos.knowledge.embeddings.embedder import get_embedder
from aaos.knowledge.embeddings.vector_store import get_vector_store


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(size - overlap, 1)
    return chunks


async def index_text(
    text: str,
    *,
    source: str,
    title: str | None = None,
    document_id: int | None = None,
) -> dict:
    chunks = chunk_text(text)
    if not chunks:
        return {"chunks": 0, "vectors": 0, "embedder": None}

    embedder = get_embedder()
    vectors = embedder.embed(chunks)
    rows = []
    for i, (content, emb) in enumerate(zip(chunks, vectors)):
        rows.append(
            {
                "document_id": document_id,
                "chunk_index": i,
                "source": source,
                "title": title or source,
                "content": content,
                "embedder": embedder.name,
                "embedding": emb,
            }
        )
    store = get_vector_store()
    n = await store.add_many(rows)
    return {
        "chunks": len(chunks),
        "vectors": n,
        "embedder": embedder.name,
        "dims": embedder.dimensions,
    }
