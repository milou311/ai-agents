import asyncio
from pathlib import Path

from aaos.knowledge.embeddings.embedder import LocalHashEmbedder, cosine
from aaos.knowledge.embeddings.vector_store import VectorStore
from aaos.knowledge.embeddings.indexer import index_text
from aaos.knowledge.embeddings.search import semantic_search


def test_local_embedder_similarity():
    e = LocalHashEmbedder()
    a = e.embed_one("الاقتصاد والاستثمار والأسواق")
    b = e.embed_one("القوة الاقتصادية والمنافسة في السوق")
    c = e.embed_one("طريقة طهي المعكرونة")
    assert cosine(a, b) > cosine(a, c)


def test_index_and_search(tmp_path: Path, monkeypatch):
    async def _run():
        vs = VectorStore(tmp_path / "vectors.db")
        await vs.init()

        # patch default store path via direct index into our vs
        from aaos.knowledge.embeddings import indexer, search as search_mod
        from aaos.knowledge.embeddings import vector_store as vs_mod

        monkeypatch.setattr(vs_mod, "_default_vs", vs)
        monkeypatch.setattr(indexer, "get_vector_store", lambda: vs)
        monkeypatch.setattr(search_mod, "get_vector_store", lambda: vs)

        await index_text(
            "بناء نظام اقتصادي يعتمد على الاستثمار والأسواق والمنافسة.",
            source="econ",
            title="econ",
            document_id=1,
        )
        hits = await semantic_search("كيف أبني اقتصاد قوي؟", limit=3)
        assert len(hits) >= 1

    asyncio.get_event_loop().run_until_complete(_run())
