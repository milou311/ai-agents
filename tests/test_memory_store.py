import asyncio
from pathlib import Path

import pytest

from aaos.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path):
    s = MemoryStore(tmp_path / "test.db")
    asyncio.get_event_loop().run_until_complete(s.init())
    return s


def test_history_roundtrip(store: MemoryStore):
    async def _run():
        await store.add_message(1, "user", "مرحبا")
        await store.add_message(1, "assistant", "أهلاً")
        hist = await store.get_history(1, limit=10)
        assert len(hist) == 2
        assert hist[0]["role"] == "user"
        assert hist[1]["content"] == "أهلاً"

    asyncio.get_event_loop().run_until_complete(_run())


def test_notes(store: MemoryStore):
    async def _run():
        await store.set_note(1, "name", "أحمد")
        assert await store.get_note(1, "name") == "أحمد"
        notes = await store.list_notes(1)
        assert any(n["key"] == "name" for n in notes)

    asyncio.get_event_loop().run_until_complete(_run())
