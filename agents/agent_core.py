"""
Agent core with tool-calling loop (multi-step automatic execution).
Primary: Groq models with automatic fallback.
Final fallback: OpenAI (if OPENAI_API_KEY is set).
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import logging
import os
import time

from groq import Groq, RateLimitError, APIStatusError

from agents.tools.web_search import web_search
from agents.tools.file_ops import read_file, write_file, list_files, delete_file
from agents.tools.tasks_tool import manage_tasks, manage_reminders, manage_notes
from agents.tools.http_api import call_api
from agents import memory

logger = logging.getLogger(__name__)

# Groq models (tried in order)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

# OpenAI fallback model
OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """أنت مساعد شخصي ذكي اسمه "مُعين".
نتحدث بالعربية المبسطة أو الدارجة حسب المستخدم، وبالإنجليزية بطلاقة.

قدراتك (استخدم الأدوات عند الحاجة):
- البحث على الإنترنت
- قراءة/كتابة الملفات
- المهام والتذكيرات والملاحظات
- استدعاء APIs
- تنفيذ عدة خطوات تلقائياً

قواعد:
- كن مختصراً وواضحاً.
- لا تختلق معلومات.
- استخدم الأدوات بدل التخمين.
- لا تذكر أسماء الأدوات التقنية إلا إذا سُئلت.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "البحث على الإنترنت",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "قراءة ملف محفوظ",
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
            "name": "write_file",
            "description": "حفظ محتوى في ملف",
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
            "description": "عرض الملفات المحفوظة",
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
            "description": "إدارة المهام: add|list|complete|cancel",
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
            "description": "ضبط تذكير",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add"]},
                    "message": {"type": "string"},
                    "minutes_from_now": {"type": "integer"},
                    "remind_at": {"type": "string"},
                },
                "required": ["action", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_notes",
            "description": "ملاحظات دائمة: set|get|list",
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
            "description": "استدعاء HTTP API",
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

RATE_LIMIT_MSG = (
    "⏳ تم استهلاك الحصة اليومية من خدمة الذكاء الاصطناعي.\n"
    "حاول مرة أخرى لاحقاً (عادةً تتجدد الحصة يومياً)."
)


class AgentCore:
    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.openai = None
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                from openai import OpenAI
                self.openai = OpenAI(api_key=openai_key)
                logger.info("OpenAI fallback enabled")
            except Exception as e:
                logger.warning("OpenAI init failed: %s", e)
        self.max_tool_rounds = 5

    def _chat_with_fallback(self, **kwargs):
        """
        1) Try all Groq models
        2) If all rate-limited → try OpenAI (if key present)
        3) Otherwise raise last error
        """
        last_error = None

        # --- Groq models ---
        for model in GROQ_MODELS:
            try:
                return self.groq.chat.completions.create(model=model, **kwargs)
            except RateLimitError as e:
                logger.warning("Rate limit on Groq/%s", model)
                last_error = e
                time.sleep(0.3)
                continue
            except APIStatusError as e:
                if e.status_code == 429:
                    logger.warning("429 on Groq/%s", model)
                    last_error = e
                    time.sleep(0.3)
                    continue
                raise

        # --- OpenAI fallback ---
        if self.openai is not None:
            try:
                logger.info("Falling back to OpenAI %s", OPENAI_MODEL)
                return self.openai.chat.completions.create(
                    model=OPENAI_MODEL,
                    **kwargs,
                )
            except Exception as e:
                # OpenAI also has RateLimitError in openai package
                err_name = type(e).__name__
                if "RateLimit" in err_name or getattr(e, "status_code", None) == 429:
                    logger.warning("OpenAI also rate-limited: %s", e)
                    last_error = e
                else:
                    logger.exception("OpenAI fallback error")
                    last_error = e

        raise last_error or RateLimitError(
            "All providers rate-limited", response=None, body=None
        )

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
        history = await memory.get_history(user_id, limit=8)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if extra_context:
            messages.append({"role": "system", "content": extra_context[:500]})
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        await memory.add_message(user_id, "user", user_message)

        try:
            for _ in range(self.max_tool_rounds):
                try:
                    response = self._chat_with_fallback(
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        temperature=0.6,
                        max_tokens=1024,
                    )
                except (RateLimitError, APIStatusError) as e:
                    if isinstance(e, RateLimitError) or getattr(e, "status_code", None) == 429:
                        await memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                        return RATE_LIMIT_MSG
                    raise
                except Exception as e:
                    # Catch OpenAI rate limit / other provider errors
                    if "RateLimit" in type(e).__name__ or getattr(e, "status_code", None) == 429:
                        await memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                        return RATE_LIMIT_MSG
                    raise

                msg = response.choices[0].message

                if not getattr(msg, "tool_calls", None):
                    reply = msg.content or ""
                    await memory.add_message(user_id, "assistant", reply)
                    return reply

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
                    if len(result) > 2000:
                        result = result[:2000] + "\n...(مقطوع)"
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        }
                    )

            final = "أنجزت أكبر عدد ممكن من الخطوات. حاول تقسيم الطلب إن أمكن."
            await memory.add_message(user_id, "assistant", final)
            return final

        except (RateLimitError, APIStatusError) as e:
            if isinstance(e, RateLimitError) or getattr(e, "status_code", None) == 429:
                await memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                return RATE_LIMIT_MSG
            logger.exception("API error")
            return f"عذراً، حدث خطأ في الخدمة: {e}"
        except Exception as e:
            if "RateLimit" in type(e).__name__:
                await memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                return RATE_LIMIT_MSG
            logger.exception("Agent run error")
            return f"عذراً، حدث خطأ: {e}"
