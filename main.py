"""
AI Agents - Main Entry Point

تشغيل بوت تليجرام المتقدم:
    python -m agents.telegram_bot

أو الواجهة النصية المحلية:
    python main.py
"""

from agents.personal_assistant import run_chat_interface

if __name__ == "__main__":
    run_chat_interface()
