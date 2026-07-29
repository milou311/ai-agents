"""
Persistent memory using SQLite.
Stores conversation history + user notes per Telegram user.
"""

import aiosqlite
import json
import os
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"


async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def get_history(user_id: int, limit: int = 30) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT role, content FROM conversations
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        # reverse to chronological order
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def add_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        await db.commit()


async def clear_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        await db.commit()


async def set_note(user_id: int, key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO notes (user_id, key, value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, key, value),
        )
        await db.commit()


async def get_note(user_id: int, key: str) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM notes WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def list_notes(user_id: int) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT key, value, updated_at FROM notes WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_task(user_id: int, title: str, description: str = "", due_date: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (user_id, title, description, due_date) VALUES (?, ?, ?, ?)",
            (user_id, title, description, due_date),
        )
        await db.commit()
        return cursor.lastrowid


async def list_tasks(user_id: int, status: str = None) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY id DESC",
                (user_id, status),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_task_status(user_id: int, task_id: int, status: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE tasks SET status = ? WHERE id = ? AND user_id = ?",
            (status, task_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def add_reminder(user_id: int, chat_id: int, message: str, remind_at: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (user_id, chat_id, message, remind_at) VALUES (?, ?, ?, ?)",
            (user_id, chat_id, message, remind_at),
        )
        await db.commit()
        return cursor.lastrowid


async def get_due_reminders(now_iso: str) -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= ?",
            (now_iso,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_reminder_sent(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()
