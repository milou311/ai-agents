"""Telegram Interface — Ops / Gemini only."""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import edge_tts

from aaos.config import get_settings
from aaos.core.agent_loop import AgentLoop
from aaos.core.supervisor import Supervisor
from aaos.identity import get_identity_manager
from aaos.memory import get_default_store
from aaos.knowledge import get_knowledge_store

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

settings = get_settings()
loop = AgentLoop()
supervisor = Supervisor(loop)
store = get_default_store()
knowledge = get_knowledge_store()
identity = get_identity_manager()

TEMP_DIR = Path(tempfile.gettempdir()) / "ops_voice"
TEMP_DIR.mkdir(exist_ok=True)


async def _run_agent(user_id: int, chat_id: int, text: str, extra: str = "") -> str:
    if settings.use_supervisor and not extra:
        return await supervisor.run(user_id, chat_id, text)
    return await loop.run(user_id, chat_id, text, extra_context=extra)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = identity.introduce("ar")
    await update.message.reply_text(
        f"{intro}\n\n"
        "✅ بحث · ملفات · مهام · تذكيرات · معرفة · صور\n\n"
        "/help · /reset · /tasks · /notes"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أرسل رسالة نصية.\n"
        "أمثلة: ابحث عن … · أضف مهمة … · من أنت؟\n"
        "/reset لمسح المحادثة"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await store.clear_history(update.effective_user.id)
    await update.message.reply_text("تم مسح ذاكرة المحادثة ✅")


async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = await store.list_tasks(update.effective_user.id)
    if not tasks:
        await update.message.reply_text("لا توجد مهام حالياً.")
        return
    lines = [
        f"#{t['id']} [{t['status']}] {t['title']}"
        + (f" | {t['due_date']}" if t.get("due_date") else "")
        for t in tasks
    ]
    await update.message.reply_text("المهام:\n" + "\n".join(lines))


async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = await store.list_notes(update.effective_user.id)
    if not notes:
        await update.message.reply_text("لا توجد ملاحظات محفوظة.")
        return
    lines = [f"• {n['key']}: {n['value']}" for n in notes]
    await update.message.reply_text("الملاحظات:\n" + "\n".join(lines))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        reply = await _run_agent(user_id, chat_id, update.message.text or "")
        for i in range(0, max(len(reply), 1), 4000):
            await update.message.reply_text(reply[i : i + 4000] or "…")
    except Exception as e:
        logger.exception("handle_text")
        await update.message.reply_text(f"عذراً، حدث خطأ: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الصوت معطّل حالياً (المزود Gemini فقط للنص). أرسل رسالة نصية."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    caption = update.message.caption or "صف هذه الصورة"
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_path = str(TEMP_DIR / f"{user_id}_{photo.file_id}.jpg")
    await file.download_to_drive(img_path)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        description = "استلمت الصورة."
        if settings.gemini_api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.gemini_api_key)
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_bytes(
                                    data=img_bytes, mime_type="image/jpeg"
                                ),
                                types.Part.from_text(text=caption),
                            ],
                        )
                    ],
                )
                description = (response.text or description).strip()
            except Exception as e:
                logger.warning("Gemini vision failed: %s", e)

        reply = await _run_agent(
            user_id,
            chat_id,
            f"[صورة] {caption}\n\nوصف: {description}",
            extra="المستخدم أرسل صورة.",
        )
        await update.message.reply_text(reply)
    except Exception as e:
        logger.exception("handle_photo")
        await update.message.reply_text(f"خطأ في معالجة الصورة: {e}")
    finally:
        try:
            os.remove(img_path)
        except OSError:
            pass


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    doc = update.message.document
    if doc.file_size and doc.file_size > 5_000_000:
        await update.message.reply_text("الملف كبير جداً (الحد 5MB).")
        return

    file = await context.bot.get_file(doc.file_id)
    filename = doc.file_name or "document.txt"
    dest = Path(settings.data_dir) / "files" / str(user_id) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    await file.download_to_drive(str(dest))

    text_exts = {".txt", ".md", ".py", ".json", ".csv", ".log", ".html", ".xml"}
    if Path(filename).suffix.lower() in text_exts:
        content = dest.read_text(encoding="utf-8", errors="replace")[:4000]
        try:
            await knowledge.ingest_text(
                f"telegram:{user_id}:{filename}", content, title=filename
            )
        except Exception:
            pass
        prompt = f"ملف '{filename}':\n\n{content}\n\nلخّصه أو ساعد حسب الطلب."
        if update.message.caption:
            prompt += f"\nالطلب: {update.message.caption}"
        reply = await _run_agent(user_id, chat_id, prompt)
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text(f"تم حفظ الملف '{filename}'.")


async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc).isoformat()
    due = await store.get_due_reminders(now)
    for r in due:
        try:
            await context.bot.send_message(
                chat_id=r["chat_id"], text=f"⏰ تذكير: {r['message']}"
            )
            await store.mark_reminder_sent(r["id"])
        except Exception as e:
            logger.error("Reminder failed: %s", e)


def build_application() -> Application:
    token = settings.telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN مفقود")
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY مفقود — https://aistudio.google.com/apikey"
        )

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("tasks", tasks_cmd))
    application.add_handler(CommandHandler("notes", notes_cmd))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    if application.job_queue:
        application.job_queue.run_repeating(check_reminders, interval=30, first=10)

    async def post_init(app: Application):
        await store.init()
        await knowledge.init()
        logger.info("Ops Telegram ready — Gemini only (%s)", settings.gemini_model)

    application.post_init = post_init
    return application


def main():
    app = build_application()
    print("🤖 Ops (Gemini only) يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
