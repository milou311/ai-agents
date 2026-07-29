"""
Personal Assistant Telegram Bot
--------------------------------
Version of the assistant that works on Telegram (perfect for phone use).
"""

import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """أنت مساعد شخصي ذكي اسمك "مُعين".
تتحدث بالعربية الفصحى المبسطة أو الدارجة حسب أسلوب المستخدم، وتتحدث الإنجليزية بطلاقة أيضاً.

قدراتك:
- مساعدة المستخدم في تنظيم أفكاره ومهامه اليومية
- تلخيص النصوص والمعلومات
- الإجابة على الأسئلة بشكل واضح ومفيد
- اقتراح حلول عملية
- التحدث بأسلوب ودود ومحترم ومهني

قواعد مهمة:
- كن مختصراً وواضحاً ما لم يطلب المستخدم التفصيل
- إذا لم تكن متأكداً من معلومة، قل ذلك بصراحة
- لا تختلق معلومات
- ركز على مساعدة المستخدم في مهامه اليومية
"""

# Store conversation history per user
user_conversations = {}


def get_user_history(user_id: int):
    if user_id not in user_conversations:
        user_conversations[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    return user_conversations[user_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "مرحباً! 👋\n\n"
        "أنا *مُعين*، مساعدك الشخصي الذكي.\n\n"
        "يمكنك التحدث معي بالعربية أو الإنجليزية.\n"
        "سأساعدك في تنظيم أفكارك، تلخيص المعلومات، والإجابة على أسئلتك.\n\n"
        "الأوامر المتاحة:\n"
        "/start - بدء المحادثة\n"
        "/reset - مسح ذاكرة المحادثة\n"
        "/help - عرض المساعدة"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        "*كيفية استخدام البوت:*\n\n"
        "• فقط أرسل أي رسالة وسأرد عليك\n"
        "• /reset - لمسح المحادثة السابقة والبدء من جديد\n"
        "• يمكنك الكتابة بالعربية أو الإنجليزية"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history for the user."""
    user_id = update.effective_user.id
    user_conversations[user_id] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    await update.message.reply_text("تم مسح ذاكرة المحادثة. يمكنك البدء من جديد ✅")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal text messages."""
    user_id = update.effective_user.id
    user_message = update.message.text

    history = get_user_history(user_id)
    history.append({"role": "user", "content": user_message})

    try:
        # Send typing action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=history,
            temperature=0.7,
            max_tokens=1000,
        )

        assistant_reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": assistant_reply})

        await update.message.reply_text(assistant_reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "عذراً، حدث خطأ أثناء معالجة رسالتك. حاول مرة أخرى."
        )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "❌ لم يتم العثور على TELEGRAM_BOT_TOKEN في ملف .env"
        )

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "❌ لم يتم العثور على OPENAI_API_KEY في ملف .env"
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("🤖 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
