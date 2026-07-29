"""Tasks, reminders, notes — use aaos.memory."""

from datetime import datetime, timedelta

from aaos.memory import get_default_store


async def manage_tasks(
    user_id: int,
    action: str,
    title: str = "",
    description: str = "",
    due_date: str | None = None,
    task_id: int | None = None,
    status: str | None = None,
) -> str:
    store = get_default_store()
    if action == "add":
        if not title:
            return "يجب تحديد عنوان المهمة."
        tid = await store.add_task(user_id, title, description, due_date)
        return f"تمت إضافة المهمة #{tid}: {title}"
    if action == "list":
        tasks = await store.list_tasks(user_id, status)
        if not tasks:
            return "لا توجد مهام."
        lines = []
        for t in tasks:
            due = f" | موعد: {t['due_date']}" if t.get("due_date") else ""
            lines.append(f"#{t['id']} [{t['status']}] {t['title']}{due}")
        return "المهام:\n" + "\n".join(lines)
    if action == "complete":
        if not task_id:
            return "يجب تحديد رقم المهمة."
        ok = await store.update_task_status(user_id, task_id, "completed")
        return f"تم إكمال المهمة #{task_id}" if ok else "المهمة غير موجودة."
    if action == "cancel":
        if not task_id:
            return "يجب تحديد رقم المهمة."
        ok = await store.update_task_status(user_id, task_id, "cancelled")
        return f"تم إلغاء المهمة #{task_id}" if ok else "المهمة غير موجودة."
    return f"إجراء غير معروف: {action}. استخدم: add, list, complete, cancel"


async def manage_reminders(
    user_id: int,
    chat_id: int,
    action: str,
    message: str = "",
    minutes_from_now: int = 0,
    remind_at: str | None = None,
) -> str:
    store = get_default_store()
    if action == "add":
        if not message:
            return "يجب كتابة نص التذكير."
        if minutes_from_now > 0:
            at = (datetime.utcnow() + timedelta(minutes=minutes_from_now)).isoformat()
        elif remind_at:
            at = remind_at
        else:
            return "حدد minutes_from_now أو remind_at."
        rid = await store.add_reminder(user_id, chat_id, message, at)
        return f"تم ضبط التذكير #{rid} في {at}"
    return "حالياً يدعم فقط action=add"


async def manage_notes(
    user_id: int,
    action: str,
    key: str = "",
    value: str = "",
) -> str:
    store = get_default_store()
    if action == "set":
        if not key or not value:
            return "يجب تحديد المفتاح والقيمة."
        await store.set_note(user_id, key, value)
        return f"تم حفظ الملاحظة: {key}"
    if action == "get":
        if not key:
            return "حدد المفتاح."
        val = await store.get_note(user_id, key)
        return val if val else f"لا توجد ملاحظة باسم '{key}'"
    if action == "list":
        notes = await store.list_notes(user_id)
        if not notes:
            return "لا توجد ملاحظات."
        return "\n".join(f"- {n['key']}: {n['value']}" for n in notes)
    return "استخدم: set, get, list"
