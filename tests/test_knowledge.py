import asyncio
from pathlib import Path

from aaos.knowledge.store import KnowledgeStore


def test_ingest_and_search(tmp_path: Path):
    async def _run():
        ks = KnowledgeStore(tmp_path / "k.db")
        await ks.ingest_text(
            "doc1",
            "مُعين هو نظام تشغيل للوكلاء الذكيين AAOS مع ذاكرة وأدوات.",
            title="aaos",
        )
        hits = await ks.search("ذاكرة أدوات")
        assert len(hits) >= 1
        text = await ks.search_as_text("AAOS")
        assert "AAOS" in text or "وكلاء" in text or "مُعين" in text

    asyncio.get_event_loop().run_until_complete(_run())
