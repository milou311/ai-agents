"""
SQLite-backed vector store (vectors as JSON float arrays).
Good for thousands–tens of thousands of chunks. Scale later with dedicated VDB.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import aiosqlite

from aaos.knowledge.embeddings.embedder import cosine


class VectorStore:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            root = Path(__file__).resolve().parents[3]
            db_path = root / "data" / "vectors.db"
        self.db_path = Path(db_path)

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    chunk_index INTEGER,
                    source TEXT,
                    title TEXT,
                    content TEXT NOT NULL,
                    embedder TEXT NOT NULL,
                    dims INTEGER NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_vectors_source ON vectors(source)"
            )
            await db.commit()

    async def add_many(
        self,
        rows: list[dict],
    ) -> int:
        """Each row: content, embedding(list[float]), embedder, source, title, document_id, chunk_index."""
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            for r in rows:
                emb = r["embedding"]
                await db.execute(
                    """
                    INSERT INTO vectors
                    (document_id, chunk_index, source, title, content, embedder, dims, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.get("document_id"),
                        r.get("chunk_index", 0),
                        r.get("source", ""),
                        r.get("title", ""),
                        r["content"],
                        r.get("embedder", "unknown"),
                        len(emb),
                        json.dumps(emb),
                    ),
                )
            await db.commit()
        return len(rows)

    async def count(self) -> int:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM vectors")
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 8,
        embedder_name: str | None = None,
    ) -> list[dict]:
        await self.init()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if embedder_name:
                cur = await db.execute(
                    "SELECT * FROM vectors WHERE embedder = ?",
                    (embedder_name,),
                )
            else:
                cur = await db.execute("SELECT * FROM vectors")
            rows = await cur.fetchall()

        scored: list[dict] = []
        for r in rows:
            try:
                emb = json.loads(r["embedding"])
            except json.JSONDecodeError:
                continue
            if len(emb) != len(query_embedding):
                continue
            score = cosine(query_embedding, emb)
            scored.append(
                {
                    "score": score,
                    "content": r["content"],
                    "source": r["source"],
                    "title": r["title"],
                    "document_id": r["document_id"],
                    "chunk_index": r["chunk_index"],
                    "mode": "semantic",
                }
            )
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]


_default_vs: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _default_vs
    if _default_vs is None:
        _default_vs = VectorStore()
    return _default_vs
