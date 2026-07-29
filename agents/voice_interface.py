"""
Voice Interface (Placeholder)
-----------------------------
This module will later support:
- Speech-to-Text (using Whisper or OpenAI Audio API)
- Text-to-Speech (OpenAI TTS or local models)

Current status: Ready for implementation.
"""

from rich.console import Console

console = Console()

def start_voice_mode():
    console.print(
        "[yellow]🎙️ وضع الصوت قيد التطوير حالياً.[/yellow]\n"
        "الواجهة النصية جاهزة للاستخدام الآن.\n"
        "لاحقاً سيتم إضافة:\n"
        "  - تحويل الصوت إلى نص (Speech-to-Text)\n"
        "  - تحويل الرد إلى صوت (Text-to-Speech)\n"
    )

if __name__ == "__main__":
    start_voice_mode()
