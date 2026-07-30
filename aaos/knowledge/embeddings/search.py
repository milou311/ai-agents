"""Semantic search facade."""

from __future__ import annotations

from aaos.knowledge.embeddings.embedder import get_embedder
from aaos.knowledge.embeddings.vector_store import get_vector_store


async def semantic_search(query: str, limit: int = 8) -> list[dict]:
    embedder = get_embedder()
    q_emb = embedder.embed_one(query)
    store = get_vector_store()
    return await store.search(
        q_emb, limit=limit, embedder_name=getattr(embedder, "name", None)
    )
