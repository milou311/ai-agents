"""
Personal Assistant Agent
------------------------
A practical AI assistant that supports Arabic & English,
can help with daily tasks, summarization, and organization.
Ready for chat interface + future voice support.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()

console = Console()

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


class PersonalAssistant:
    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ لم يتم العثور على OPENAI_API_KEY.\n"
                "قم بإنشاء ملف .env وضع فيه: OPENAI_API_KEY=sk-..."
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.conversation_history: List[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_message: str) -> str:
        """إرسال رسالة والحصول على رد"""
        self.conversation_history.append(
            {"role": "user", "content": user_message}
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=1000,
            )

            assistant_message = response.choices[0].message.content
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_message}
            )
            return assistant_message

        except Exception as e:
            return f"⚠️ حدث خطأ: {str(e)}"

    def reset(self):
        """إعادة تعيين المحادثة"""
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        console.print("[yellow]تم إعادة تعيين المحادثة.[/yellow]")


def run_chat_interface():
    """واجهة محادثة نصية تفاعلية"""
    console.print(
        Panel.fit(
            "[bold blue]مُعين[/bold blue] - مساعدك الشخصي الذكي\n"
            "اكتب رسالتك بالعربية أو الإنجليزية\n"
            "أوامر خاصة: [bold]/reset[/bold] لإعادة التعيين | [bold]/exit[/bold] للخروج",
            title="Personal Assistant Agent",
            border_style="blue",
        )
    )

    try:
        agent = PersonalAssistant()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return

    while True:
        try:
            user_input = console.input("\n[bold green]أنت:[/bold green] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["/exit", "exit", "خروج", "quit"]:
                console.print("[blue]إلى اللقاء! 👋[/blue]")
                break

            if user_input.lower() in ["/reset", "reset", "إعادة"]:
                agent.reset()
                continue

            with console.status("[bold blue]جاري التفكير...[/bold blue]"):
                reply = agent.chat(user_input)

            console.print("\n[bold blue]مُعين:[/bold blue]")
            console.print(Markdown(reply))

        except KeyboardInterrupt:
            console.print("\n[blue]تم الإيقاف. إلى اللقاء! 👋[/blue]")
            break


if __name__ == "__main__":
    run_chat_interface()
