"""Task, reminder and notes management tools."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents import memory
from datetime import datetime, timedelta


async def manage_tasks(
    user_id: int,
    action: str,
    title: str = "",
    description: str = "",
    due_date: str = None,
    task_id: int = None,
    status: str = None,
) -> str:
    if action == "add":
        if not title:
            return "يجب تحديد عنوان المهمة."
        tid = await memory.add_task(user_id, title, description, due_date)
        return f"تمت إضافة المهمة #{tid}: {title}"

    elif action == "list":
        tasks = await memory.list_tasks(user_id, status)
        if not tasks:
            return "لا توجد مهام."
        lines = []
        for t in tasks:
            due = f" | موعد: {t['due_date']}" if t.get("due_date") else ""
            lines.append(f"#{t['id']} [{t['status']}] {t['title']}{due}")
        return "المهام:\n" + "\n".join(lines)

    elif action == "complete":
        if not task_id:
            return "يجب تحديد رقم المهمة."
        ok = await memory.update_task_status(user_id, task_id, "completed")
        return f"تم إكمال المهمة #{task_id}" if ok else "المهمة غير موجودة."

    elif action == "cancel":
        if not task_id:
            return "يجب تحديد رقم المهمة."
        ok = await memory.update_task_status(user_id, task_id, "cancelled")
        return f"تم إلغاء المهمة #{task_id}" if ok else "المهمة غير موجودة."

    return f"إجراء غير معروف: {action}. استخدم: add, list, complete, cancel"


async def manage_reminders(
    user_id: int,
    chat_id: int,
    action: str,
    message: str = "",
    minutes_from_now: int = 0,
    remind_at: str = None,
) -> str:
    if action == "add":
        if not message:
            return "يجب كتابة نص التذكير."
        if minutes_from_now > 0:
            at = (datetime.utcnow() + timedelta(minutes=minutes_from_now)).isoformat()
        elif remind_at:
            at = remind_at
        else:
            return "حدد minutes_from_now أو remind_at."
        rid = await memory.add_reminder(user_id, chat_id, message, at)
        return f"تم ضبط التذكير #{rid} في {at}"
    return "حالياً يدعم فقط action=add"


async def manage_notes(
    user_id: int,
    action: str,
    key: str = "",
    value: str = "",
) -> str:
    if action == "set":
        if not key or not value:
            return "يجب تحديد المفتاح والقيمة."
        await memory.set_note(user_id, key, value)
        return f"تم حفظ الملاحظة: {key}"
    elif action == "get":
        if not key:
            return "حدد المفتاح."
        val = await memory.get_note(user_id, key)
        return val if val else f"لا توجد ملاحظة باسم '{key}'"
    elif action == "list":
        notes = await memory.list_notes(user_id)
        if not notes:
            return "لا توجد ملاحظات."
        return "\n".join(f"- {n['key']}: {n['value']}" for n in notes)
    return "استخدم: set, get, list"
