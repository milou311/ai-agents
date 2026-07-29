"""
Long-term + working memory (SQLite).

Implements the MemoryGateway contract used by Core.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import aiosqlite

from aaos.config import get_settings


class MemoryStore:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            settings = get_settings()
            db_path = Path(settings.data_dir) / "memory.db"
        self.db_path = Path(db_path)

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, key)
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    due_date TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    remind_at TEXT NOT NULL,
                    sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    # --- Working memory (conversation) ---

    async def get_history(self, user_id: int | str, limit: int = 8) -> List[dict]:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT role, content FROM conversations
                WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (uid, limit),
            )
            rows = await cursor.fetchall()
            return [
                {"role": r["role"], "content": r["content"]} for r in reversed(rows)
            ]

    async def add_message(self, user_id: int | str, role: str, content: str) -> None:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                (uid, role, content),
            )
            await db.commit()

    async def clear_history(self, user_id: int | str) -> None:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM conversations WHERE user_id = ?", (uid,))
            await db.commit()

    # --- Notes ---

    async def set_note(self, user_id: int | str, key: str, value: str) -> None:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO notes (user_id, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (uid, key, value),
            )
            await db.commit()

    async def get_note(self, user_id: int | str, key: str) -> Optional[str]:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT value FROM notes WHERE user_id = ? AND key = ?",
                (uid, key),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def list_notes(self, user_id: int | str) -> List[dict]:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT key, value, updated_at FROM notes WHERE user_id = ?",
                (uid,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- Tasks ---

    async def add_task(
        self,
        user_id: int | str,
        title: str,
        description: str = "",
        due_date: str | None = None,
    ) -> int:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, title, description, due_date) VALUES (?, ?, ?, ?)",
                (uid, title, description, due_date),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_tasks(
        self, user_id: int | str, status: str | None = None
    ) -> List[dict]:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY id DESC",
                    (uid, status),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
                    (uid,),
                )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_task_status(
        self, user_id: int | str, task_id: int, status: str
    ) -> bool:
        uid = int(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
                (status, task_id, uid),
            )
            await db.commit()
            return cursor.rowcount > 0

    # --- Reminders ---

    async def add_reminder(
        self, user_id: int | str, chat_id: int | str, message: str, remind_at: str
    ) -> int:
        uid = int(user_id)
        cid = int(chat_id)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO reminders (user_id, chat_id, message, remind_at) VALUES (?, ?, ?, ?)",
                (uid, cid, message, remind_at),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_due_reminders(self, now_iso: str) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= ?",
                (now_iso,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def mark_reminder_sent(self, reminder_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,)
            )
            await db.commit()


# Process-wide default store (same DB path as legacy)
_default_store: MemoryStore | None = None


def get_default_store() -> MemoryStore:
    global _default_store
    if _default_store is None:
        # Preserve legacy path: <repo>/data/memory.db
        root = Path(__file__).resolve().parents[2]
        _default_store = MemoryStore(root / "data" / "memory.db")
    return _default_store
