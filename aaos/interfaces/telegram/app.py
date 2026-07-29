"""
Telegram Interface Adapter (AAOS).

Translates Telegram updates ↔ AgentRequest / AgentLoop.
No business logic beyond channel concerns (voice, photos, commands UI).
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
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
from groq import Groq, RateLimitError, APIStatusError
import edge_tts

from aaos.config import get_settings
from aaos.core.agent_loop import AgentLoop
from aaos.core.types import AgentRequest
from aaos.memory import get_default_store

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

settings = get_settings()
loop = AgentLoop()
store = get_default_store()
groq_client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

TEMP_DIR = Path(tempfile.gettempdir()) / "mueen_voice"
TEMP_DIR.mkdir(exist_ok=True)

RATE_LIMIT_MSG = (
    "⏳ تم استهلاك الحصة اليومية من خدمة الذكاء الاصطناعي.\n"
    "حاول مرة أخرى لاحقاً (عادةً تتجدد الحصة يومياً)."
)


async def _run_agent(user_id: int, chat_id: int, text: str, extra: str = "") -> str:
    return await loop.run(user_id, chat_id, text, extra_context=extra)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "مرحباً! 👋\n\n"
        "أنا *مُعين*، مساعدك الشخصي الذكي.\n\n"
        "✅ البحث · الملفات · المهام · التذكيرات · الملاحظات · الصوت · الصور\n\n"
        "/help · /reset · /tasks · /notes"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أرسل رسالة نصية أو صوتية.\n"
        "أمثلة: ابحث عن … · أضف مهمة … · ذكّرني بعد 30 دقيقة · احفظ ملاحظة …\n"
        "/reset لمسح المحادثة",
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
    lines = [f"• *{n['key']}*: {n['value']}" for n in notes]
    await update.message.reply_text("الملاحظات:\n" + "\n".join(lines), parse_mode="Markdown")


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


async def transcribe_voice(file_path: str) -> str:
    if not groq_client:
        raise RuntimeError("Groq not configured for STT")
    with open(file_path, "rb") as f:
        transcription = groq_client.audio.transcriptions.create(
            file=(Path(file_path).name, f.read()),
            model="whisper-large-v3",
            language="ar",
            response_format="text",
        )
    return transcription if isinstance(transcription, str) else transcription.text


async def text_to_speech(text: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text, "ar-SA-HamedNeural")
    await communicate.save(out_path)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("لم أستطع قراءة الملف الصوتي.")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    file = await context.bot.get_file(voice.file_id)
    ogg_path = str(TEMP_DIR / f"{user_id}_{voice.file_id}.ogg")
    await file.download_to_drive(ogg_path)

    try:
        try:
            transcript = await transcribe_voice(ogg_path)
        except (RateLimitError, APIStatusError):
            await update.message.reply_text(RATE_LIMIT_MSG)
            return

        if not (transcript or "").strip():
            await update.message.reply_text("لم أتمكن من فهم الصوت.")
            return

        await update.message.reply_text(f"🎤 سمعت: {transcript}")
        reply = await _run_agent(user_id, chat_id, transcript)
        for i in range(0, max(len(reply), 1), 4000):
            await update.message.reply_text(reply[i : i + 4000] or "…")

        if len(reply) < 500 and RATE_LIMIT_MSG not in reply:
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
                mp3_path = str(TEMP_DIR / f"{user_id}_reply.mp3")
                await text_to_speech(reply, mp3_path)
                with open(mp3_path, "rb") as audio_file:
                    await update.message.reply_voice(voice=InputFile(audio_file))
                os.remove(mp3_path)
            except Exception:
                pass
    except Exception as e:
        logger.exception("handle_voice")
        await update.message.reply_text(f"خطأ في معالجة الصوت: {e}")
    finally:
        try:
            os.remove(ogg_path)
        except OSError:
            pass


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
        description = (
            "استلمت الصورة. صف ما تريد وسأساعدك."
        )
        if groq_client:
            try:
                import base64

                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                response = groq_client.chat.completions.create(
                    model="llama-3.2-90b-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": caption},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64}"
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=512,
                )
                description = response.choices[0].message.content
            except (RateLimitError, APIStatusError):
                await update.message.reply_text(RATE_LIMIT_MSG)
                return
            except Exception:
                pass

        reply = await _run_agent(
            user_id,
            chat_id,
            f"[صورة] {caption}\n\nوصف الصورة: {description}",
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
    if not settings.groq_api_key and not settings.openai_api_key:
        raise ValueError("يلزم GROQ_API_KEY أو OPENAI_API_KEY")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("tasks", tasks_cmd))
    application.add_handler(CommandHandler("notes", notes_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    if application.job_queue:
        application.job_queue.run_repeating(check_reminders, interval=30, first=10)

    async def post_init(app: Application):
        await store.init()
        logger.info("AAOS Telegram interface ready")

    application.post_init = post_init
    return application


def main():
    app = build_application()
    print("🤖 مُعين (AAOS Telegram Interface) يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
