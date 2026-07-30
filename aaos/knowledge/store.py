"""
Knowledge Engine — keyword store + semantic (vector) retrieval.

Ingest always writes:
  1) documents/chunks in knowledge.db (keyword fallback)
  2) embeddings in vectors.db (semantic search)
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

import aiosqlite

from aaos.knowledge.embeddings.indexer import chunk_text, index_text
from aaos.knowledge.embeddings.search import semantic_search
from aaos.knowledge.loaders import load_document


class KnowledgeStore:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            root = Path(__file__).resolve().parents[2]
            db_path = root / "data" / "knowledge.db"
        self.db_path = Path(db_path)

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    title TEXT,
                    content_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_content ON chunks(content)"
            )
            await db.commit()

        # ensure vector db exists
        from aaos.knowledge.embeddings.vector_store import get_vector_store

        await get_vector_store().init()

    async def ingest_text(
        self, source: str, text: str, title: str | None = None
    ) -> dict:
        await self.init()
        h = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        chunks = chunk_text(text)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO documents (source, title, content_hash) VALUES (?, ?, ?)",
                (source, title or source, h),
            )
            doc_id = cursor.lastrowid
            for i, c in enumerate(chunks):
                await db.execute(
                    "INSERT INTO chunks (document_id, chunk_index, content) VALUES (?, ?, ?)",
                    (doc_id, i, c),
                )
            await db.commit()

        semantic = await index_text(
            text, source=source, title=title or source, document_id=doc_id
        )
        return {
            "document_id": doc_id,
            "chunks": len(chunks),
            "source": source,
            "semantic": semantic,
        }

    async def ingest_file(self, path: str | Path) -> dict:
        path = Path(path)
        text = load_document(path)
        return await self.ingest_text(str(path), text, title=path.name)

    async def _keyword_search(self, query: str, limit: int = 5) -> list[dict]:
        await self.init()
        terms = [t for t in re.split(r"\s+", query.strip()) if len(t) > 1][:8]
        if not terms:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT c.content, d.source, d.title, c.id
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                ORDER BY c.id DESC
                LIMIT 500
                """
            )
            rows = await cursor.fetchall()

        scored = []
        q_lower = query.lower()
        for r in rows:
            content = r["content"]
            cl = content.lower()
            score = sum(1 for t in terms if t.lower() in cl)
            if q_lower in cl:
                score += 3
            if score > 0:
                scored.append(
                    {
                        "score": float(score),
                        "content": content,
                        "source": r["source"],
                        "title": r["title"],
                        "mode": "keyword",
                    }
                )
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]

    async def search(self, query: str, limit: int = 8) -> list[dict]:
        """Prefer semantic hits; merge with keyword if needed."""
        semantic: list[dict] = []
        try:
            semantic = await semantic_search(query, limit=limit)
        except Exception:
            semantic = []

        # Keep reasonable similarity threshold for local embedder
        semantic = [h for h in semantic if h.get("score", 0) > 0.05]

        if len(semantic) >= limit:
            return semantic[:limit]

        keyword = await self._keyword_search(query, limit=limit)
        # Merge by content dedupe
        seen = {h["content"][:120] for h in semantic}
        for h in keyword:
            key = h["content"][:120]
            if key not in seen:
                semantic.append(h)
                seen.add(key)
            if len(semantic) >= limit:
                break
        return semantic[:limit]

    async def search_as_text(self, query: str, limit: int = 8) -> str:
        hits = await self.search(query, limit=limit)
        if not hits:
            return "لا نتائج في قاعدة المعرفة."
        parts = []
        for i, h in enumerate(hits, 1):
            mode = h.get("mode", "?")
            score = h.get("score", 0)
            parts.append(
                f"{i}. [{h.get('title') or h.get('source')}] "
                f"({mode} score={score:.3f})\n{h['content']}"
            )
        return "\n\n".join(parts)


_default_knowledge: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    global _default_knowledge
    if _default_knowledge is None:
        _default_knowledge = KnowledgeStore()
    return _default_knowledge
