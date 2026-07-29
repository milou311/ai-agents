"""
مُعین — Advanced Personal Assistant Telegram Bot
-------------------------------------------------
Features:
- Tool calling (web search, files, tasks, reminders, notes, APIs)
- Multi-step automatic task execution
- Persistent SQLite memory
- Voice messages (STT via Groq Whisper + TTS via edge-tts)
- Image / document handling
- Reminders background job
"""

import sys
from pathlib import Path

# Bootstrap: make project root importable when run as script
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import os
import logging
import tempfile
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from groq import Groq
import edge_tts

from agents.agent_core import AgentCore
from agents import memory

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
agent = AgentCore()

TEMP_DIR = Path(tempfile.gettempdir()) / "mueen_voice"
TEMP_DIR.mkdir(exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "مرحباً! 👋\n\n"
        "أنا *مُعين*، مساعدك الشخصي الذكي المتقدم.\n\n"
        "✅ ما يمكنني فعله:\n"
        "• البحث على الإنترنت\n"
        "• قراءة وكتابة الملفات\n"
        "• إدارة المهام والتذكيرات\n"
        "• حفظ ملاحظات دائمة\n"
        "• الاتصال بواجهات API\n"
        "• تنفيذ مهام متعددة تلقائياً\n"
        "• فهم الرسائل الصوتية والرد بصوت\n"
        "• التعامل مع الصور والمستندات\n\n"
        "الأوامر:\n"
        "/start — بدء\n"
        "/help — مساعدة\n"
        "/reset — مسح ذاكرة المحادثة\n"
        "/tasks — عرض المهام\n"
        "/notes — عرض الملاحظات"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*كيفية الاستخدام:*\n\n"
        "• أرسل أي رسالة نصية أو صوتية\n"
        "• قل مثلاً: «ابحث عن آخر أخبار الذكاء الاصطناعي»\n"
        "• أو: «أضف مهمة: شراء الحليب غداً»\n"
        "• أو: «احفظ ملاحظة اسمي أحمد»\n"
        "• أو: «ذكّرني بعد 30 دقيقة بالاتصال»\n"
        "• أو أرسل صورة وسأصفها\n\n"
        "/reset — مسح المحادثة\n"
        "/tasks — قائمة المهام\n"
        "/notes — الملاحظات المحفوظة"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await memory.clear_history(user_id)
    await update.message.reply_text("تم مسح ذاكرة المحادثة ✅ يمكنك البدء من جديد.")


async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = await memory.list_tasks(user_id)
    if not tasks:
        await update.message.reply_text("لا توجد مهام حالياً.")
        return
    lines = []
    for t in tasks:
        due = f" | {t['due_date']}" if t.get("due_date") else ""
        lines.append(f"#{t['id']} [{t['status']}] {t['title']}{due}")
    await update.message.reply_text("المهام:\n" + "\n".join(lines))


async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    notes = await memory.list_notes(user_id)
    if not notes:
        await update.message.reply_text("لا توجد ملاحظات محفوظة.")
        return
    lines = [f"• *{n['key']}*: {n['value']}" for n in notes]
    await update.message.reply_text("الملاحظات:\n" + "\n".join(lines), parse_mode="Markdown")


async def transcribe_voice(file_path: str) -> str:
    with open(file_path, "rb") as f:
        transcription = groq_client.audio.transcriptions.create(
            file=(Path(file_path).name, f.read()),
            model="whisper-large-v3",
            language="ar",
            response_format="text",
        )
    return transcription if isinstance(transcription, str) else transcription.text


async def text_to_speech(text: str, out_path: str, voice: str = "ar-SA-HamedNeural") -> str:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)
    return out_path


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        reply = await agent.run(user_id, chat_id, text)
        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i : i + 4000])
        else:
            await update.message.reply_text(reply)
    except Exception as e:
        logger.exception("handle_text error")
        await update.message.reply_text(f"عذراً، حدث خطأ: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("لم أستطع قراءة الملف الصوتي.")
        return

    file = await context.bot.get_file(voice.file_id)
    ogg_path = str(TEMP_DIR / f"{user_id}_{voice.file_id}.ogg")
    await file.download_to_drive(ogg_path)

    try:
        transcript = await transcribe_voice(ogg_path)
        if not transcript.strip():
            await update.message.reply_text("لم أتمكن من فهم الصوت. حاول مرة أخرى.")
            return

        await update.message.reply_text(f"🎤 سمعت: {transcript}")

        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        reply = await agent.run(user_id, chat_id, transcript)

        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i : i + 4000])
        else:
            await update.message.reply_text(reply)

        if len(reply) < 500:
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
            mp3_path = str(TEMP_DIR / f"{user_id}_reply.mp3")
            await text_to_speech(reply, mp3_path)
            with open(mp3_path, "rb") as audio_file:
                await update.message.reply_voice(voice=InputFile(audio_file))
            try:
                os.remove(mp3_path)
            except OSError:
                pass

    except Exception as e:
        logger.exception("handle_voice error")
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
        with open(img_path, "rb") as f:
            import base64
            b64 = base64.b64encode(f.read()).decode()

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": caption},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                            },
                        ],
                    }
                ],
                max_tokens=1024,
            )
            description = response.choices[0].message.content
        except Exception:
            description = (
                "استلمت الصورة. حالياً نموذج الرؤية غير متاح مؤقتاً، "
                "لكن يمكنك وصف ما تريد فعله بها وسأساعدك."
            )

        reply = await agent.run(
            user_id,
            chat_id,
            f"[صورة] {caption}\n\nوصف الصورة: {description}",
            extra_context="المستخدم أرسل صورة. استخدم الوصف أعلاه للرد.",
        )
        await update.message.reply_text(reply)

    except Exception as e:
        logger.exception("handle_photo error")
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
    dest = Path(__file__).resolve().parent.parent / "data" / "files" / str(user_id) / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    await file.download_to_drive(str(dest))

    text_exts = {".txt", ".md", ".py", ".json", ".csv", ".log", ".html", ".xml"}
    if Path(filename).suffix.lower() in text_exts:
        content = dest.read_text(encoding="utf-8", errors="replace")[:8000]
        prompt = f"المستخدم أرسل ملف '{filename}'. هذا محتواه:\n\n{content}\n\nلخّصه أو ساعد حسب طلبه."
        if update.message.caption:
            prompt += f"\nطلب المستخدم: {update.message.caption}"
        reply = await agent.run(user_id, chat_id, prompt)
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text(
            f"تم حفظ الملف '{filename}'. يمكنك طلب قراءته لاحقاً إن كان نصياً."
        )


async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc).isoformat()
    due = await memory.get_due_reminders(now)
    for r in due:
        try:
            await context.bot.send_message(
                chat_id=r["chat_id"],
                text=f"⏰ تذكير: {r['message']}",
            )
            await memory.mark_reminder_sent(r["id"])
        except Exception as e:
            logger.error(f"Reminder send failed: {e}")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN مفقود في .env")
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("❌ GROQ_API_KEY مفقود في .env")

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
        await memory.init_db()
        logger.info("Database ready")

    application.post_init = post_init

    print("🤖 مُعين يعمل الآن (نسخة متقدمة)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
