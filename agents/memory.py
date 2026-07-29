"""
Legacy memory API — compatibility shim over aaos.memory.MemoryStore.

Keeps the same function signatures so existing telegram_bot / tools keep working.
Same database file: data/memory.db
"""

from __future__ import annotations

from typing import List, Optional

from aaos.memory import get_default_store


async def init_db():
    await get_default_store().init()


async def get_history(user_id: int, limit: int = 30) -> List[dict]:
    return await get_default_store().get_history(user_id, limit)


async def add_message(user_id: int, role: str, content: str):
    await get_default_store().add_message(user_id, role, content)


async def clear_history(user_id: int):
    await get_default_store().clear_history(user_id)


async def set_note(user_id: int, key: str, value: str):
    await get_default_store().set_note(user_id, key, value)


async def get_note(user_id: int, key: str) -> Optional[str]:
    return await get_default_store().get_note(user_id, key)


async def list_notes(user_id: int) -> List[dict]:
    return await get_default_store().list_notes(user_id)


async def add_task(
    user_id: int, title: str, description: str = "", due_date: str = None
) -> int:
    return await get_default_store().add_task(user_id, title, description, due_date)


async def list_tasks(user_id: int, status: str = None) -> List[dict]:
    return await get_default_store().list_tasks(user_id, status)


async def update_task_status(user_id: int, task_id: int, status: str) -> bool:
    return await get_default_store().update_task_status(user_id, task_id, status)


async def add_reminder(user_id: int, chat_id: int, message: str, remind_at: str) -> int:
    return await get_default_store().add_reminder(user_id, chat_id, message, remind_at)


async def get_due_reminders(now_iso: str) -> List[dict]:
    return await get_default_store().get_due_reminders(now_iso)


async def mark_reminder_sent(reminder_id: int):
    await get_default_store().mark_reminder_sent(reminder_id)
