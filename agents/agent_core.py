"""
Agent core with tool-calling loop (multi-step automatic execution).
Uses Groq + Llama models that support tools.
"""

import json
import logging
from typing import List, Optional
from groq import Groq
import os

from agents.tools.web_search import web_search
from agents.tools.file_ops import read_file, write_file, list_files, delete_file
from agents.tools.tasks_tool import manage_tasks, manage_reminders, manage_notes
from agents.tools.http_api import call_api
from agents import memory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت مساعد شخصي ذكي اسمه "مُعين".

تتحدث بالعربية الفصحى المبسطة أو الدارجة حسب أسلوب المستخدم، وبالإنجليزية بطلاقة.

## قدراتك الحقيقية (استخدم الأدوات عند الحاجة):
1. **البحث على الإنترنت** — عندما يحتاج المستخدم معلومات حديثة أو حقائق.
2. **قراءة وكتابة الملفات** — احفظ ملاحظات طويلة، قوائم، أكواد، ملخصات.
3. **المهام والتذكيرات** — أضف مهام، أكملها، اضبط تذكيرات.
4. **الملاحظات الدائمة** — احفظ معلومات مهمة عن المستخدم (اسمه، تفضيلاته...).
5. **استدعاء APIs** — اتصل بأي واجهة HTTP عامة.
6. **تنفيذ مهام متعددة تلقائياً** — يمكنك استدعاء عدة أدوات متتالية حتى تنجز المطلوب.

## قواعد السلوك:
- كن مختصراً وواضحاً ما لم يُطلب التفصيل.
- إذا لم تكن متأكداً، قل ذلك ولا تختلق معلومات.
- استخدم الأدوات بدلاً من التخمين عندما تكون المعلومة قابلة للبحث أو الحفظ.
- بعد استخدام أداة، لخّص النتيجة للمستخدم بشكل مفيد.
- لا تذكر أسماء الأدوات التقنية للمستخدم إلا إذا سأل.
- كن ودوداً ومحترماً ومهنياً.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "البحث على الإنترنت عن معلومات حديثة أو عامة",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "نص البحث"},
                    "max_results": {"type": "integer", "description": "عدد النتائج (افتراضي 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "قراءة محتوى ملف محفوظ للمستخدم",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "اسم الملف"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "كتابة أو حفظ محتوى في ملف",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "عرض قائمة الملفات المحفوظة للمستخدم",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "حذف ملف",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_tasks",
            "description": "إدارة المهام: إضافة، عرض، إكمال، إلغاء",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "list", "complete", "cancel"],
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "due_date": {"type": "string"},
                    "task_id": {"type": "integer"},
                    "status": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_reminders",
            "description": "ضبط تذكير يُرسل لاحقاً عبر تليجرام",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add"]},
                    "message": {"type": "string"},
                    "minutes_from_now": {"type": "integer"},
                    "remind_at": {"type": "string", "description": "ISO datetime"},
                },
                "required": ["action", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_notes",
            "description": "حفظ أو استرجاع ملاحظات دائمة عن المستخدم",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["set", "get", "list"]},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_api",
            "description": "استدعاء واجهة HTTP API خارجية (GET/POST)",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT"]},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                },
                "required": ["url"],
            },
        },
    },
]


class AgentCore:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.max_tool_rounds = 8  # multi-step automatic execution

    async def _execute_tool(self, name: str, args: dict, user_id: int, chat_id: int) -> str:
        try:
            if name == "web_search":
                return web_search(args.get("query", ""), args.get("max_results", 5))
            elif name == "read_file":
                return read_file(user_id, args.get("filename", ""))
            elif name == "write_file":
                return write_file(user_id, args.get("filename", ""), args.get("content", ""))
            elif name == "list_files":
                return list_files(user_id)
            elif name == "delete_file":
                return delete_file(user_id, args.get("filename", ""))
            elif name == "manage_tasks":
                return await manage_tasks(
                    user_id,
                    action=args.get("action", "list"),
                    title=args.get("title", ""),
                    description=args.get("description", ""),
                    due_date=args.get("due_date"),
                    task_id=args.get("task_id"),
                    status=args.get("status"),
                )
            elif name == "manage_reminders":
                return await manage_reminders(
                    user_id,
                    chat_id,
                    action=args.get("action", "add"),
                    message=args.get("message", ""),
                    minutes_from_now=args.get("minutes_from_now", 0),
                    remind_at=args.get("remind_at"),
                )
            elif name == "manage_notes":
                return await manage_notes(
                    user_id,
                    action=args.get("action", "list"),
                    key=args.get("key", ""),
                    value=args.get("value", ""),
                )
            elif name == "call_api":
                return call_api(
                    url=args.get("url", ""),
                    method=args.get("method", "GET"),
                    headers=args.get("headers"),
                    body=args.get("body"),
                )
            else:
                return f"أداة غير معروفة: {name}"
        except Exception as e:
            logger.exception("Tool error")
            return f"خطأ أثناء تنفيذ الأداة: {e}"

    async def run(
        self,
        user_id: int,
        chat_id: int,
        user_message: str,
        extra_context: str = "",
    ) -> str:
        history = await memory.get_history(user_id, limit=20)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if extra_context:
            messages.append({"role": "system", "content": extra_context})
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        await memory.add_message(user_id, "user", user_message)

        for _ in range(self.max_tool_rounds):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.6,
                max_tokens=2048,
            )

            msg = response.choices[0].message

            # No tool calls → final answer
            if not msg.tool_calls:
                reply = msg.content or ""
                await memory.add_message(user_id, "assistant", reply)
                return reply

            # Append assistant message with tool_calls
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await self._execute_tool(name, args, user_id, chat_id)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        # Safety: if still looping
        final = "أنجزت أكبر عدد ممكن من الخطوات. حاول تقسيم الطلب إن أمكن."
        await memory.add_message(user_id, "assistant", final)
        return final
