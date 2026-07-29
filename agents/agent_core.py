"""
Agent core with tool-calling loop.
Primary: Groq (with robust tool_use_failed handling).
Final fallback: OpenAI if OPENAI_API_KEY is set.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import logging
import os
import re
import time

from groq import Groq, RateLimitError, APIStatusError

from agents.tools.web_search import web_search
from agents.tools.file_ops import read_file, write_file, list_files, delete_file
from agents.tools.tasks_tool import manage_tasks, manage_reminders, manage_notes
from agents.tools.http_api import call_api
from agents import memory

logger = logging.getLogger(__name__)

# Models that support tool calling reliably on Groq
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """أنت مساعد شخصي ذكي اسمه "مُعين".
نتحدث بالعربية المبسطة أو الدارجة حسب المستخدم، وبالإنجليزية بطلاقة.

قدراتك (استخدم الأدوات عند الحاجة فقط):
- البحث على الإنترنت للمعلومات الحديثة
- قراءة/كتابة الملفات
- المهام والتذكيرات والملاحظات الدائمة
- استدعاء APIs

قواعد مهمة:
- كن مختصراً وواضحاً.
- لا تختلق معلومات.
- إذا لم تجد معلومة في الذاكرة أو الأدوات، قل ذلك بصراحة.
- أجب مباشرة على الأسئلة العامة دون أدوات إذا لم تكن بحاجة لبحث أو حفظ.
- لا تذكر أسماء الأدوات التقنية إلا إذا سُئلت.
"""

# Schemas kept simple for better Groq compatibility
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet for current information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a saved user file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File name"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Save content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File name"},
                    "content": {"type": "string", "description": "File content"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List saved files for the user",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a saved file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "File name"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_tasks",
            "description": "Manage tasks. action must be one of: add, list, complete, cancel",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "add | list | complete | cancel",
                    },
                    "title": {"type": "string", "description": "Task title (for add)"},
                    "description": {"type": "string", "description": "Task details"},
                    "due_date": {"type": "string", "description": "Optional due date"},
                    "task_id": {"type": "integer", "description": "Task id (for complete/cancel)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_reminders",
            "description": "Set a reminder. action must be add",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "Must be: add"},
                    "message": {"type": "string", "description": "Reminder text"},
                    "minutes_from_now": {
                        "type": "integer",
                        "description": "Minutes from now",
                    },
                },
                "required": ["action", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_notes",
            "description": "Permanent notes. action must be one of: set, get, list",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "set | get | list",
                    },
                    "key": {"type": "string", "description": "Note key"},
                    "value": {"type": "string", "description": "Note value (for set)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_api",
            "description": "Call an external HTTP API",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL"},
                    "method": {
                        "type": "string",
                        "description": "GET, POST, or PUT",
                    },
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


def _is_rate_limit(e: Exception) -> bool:
    if isinstance(e, RateLimitError):
        return True
    if getattr(e, "status_code", None) == 429:
        return True
    if "RateLimit" in type(e).__name__:
        return True
    return False


def _is_tool_use_failed(e: Exception) -> bool:
    """Groq returns 400 with tool_use_failed when model emits bad tool XML."""
    status = getattr(e, "status_code", None)
    if status != 400:
        return False
    text = str(e).lower()
    return "tool_use_failed" in text or "failed to call a function" in text


def _parse_xml_tool_call(text: str):
    """
    Parse Groq-style failed generation like:
    <function=manage_notes{"action":"get","key":"x"}</function>
    Returns (name, args_dict) or None.
    """
    if not text:
        return None
    m = re.search(
        r"<function[=\s]*([a-zA-Z0-9_]+)\s*(\{.*?")\s*</function>",
        text,
        re.DOTALL,
    )
    if not m:
        # alternate form: <function=name>{...}</function>
        m = re.search(
            r"<function[=\s]*([a-zA-Z0-9_]+)\s*>\s*(\{.*?\})\s*</function>",
            text,
            re.DOTALL,
        )
    if not m:
        m = re.search(r"<function=([a-zA-Z0-9_]+)\s*(\{[^<]*\})", text, re.DOTALL)
    if not m:
        return None
    name = m.group(1).strip()
    try:
        args = json.loads(m.group(2))
    except json.JSONDecodeError:
        args = {}
    return name, args


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

    def _chat(self, *, use_tools: bool, model: str, provider: str, **kwargs):
        call_kwargs = dict(kwargs)
        if use_tools:
            call_kwargs["tools"] = TOOLS
            call_kwargs["tool_choice"] = "auto"
        else:
            call_kwargs.pop("tools", None)
            call_kwargs.pop("tool_choice", None)

        if provider == "groq":
            return self.groq.chat.completions.create(model=model, **call_kwargs)
        if provider == "openai" and self.openai is not None:
            return self.openai.chat.completions.create(model=model, **call_kwargs)
        raise RuntimeError(f"Unknown provider: {provider}")

    def _chat_with_fallback(self, messages, use_tools=True, **kwargs):
        """
        Try Groq models, then OpenAI.
        On tool_use_failed: retry same model without tools, or parse XML tool call.
        """
        last_error = None
        providers = [(m, "groq") for m in GROQ_MODELS]
        if self.openai is not None:
            providers.append((OPENAI_MODEL, "openai"))

        for model, provider in providers:
            try:
                return self._chat(
                    use_tools=use_tools,
                    model=model,
                    provider=provider,
                    messages=messages,
                    temperature=0.5,
                    max_tokens=1024,
                    **kwargs,
                )
            except Exception as e:
                if _is_rate_limit(e):
                    logger.warning("Rate limit on %s/%s", provider, model)
                    last_error = e
                    time.sleep(0.3)
                    continue

                if use_tools and _is_tool_use_failed(e):
                    logger.warning(
                        "tool_use_failed on %s/%s — retrying without tools",
                        provider,
                        model,
                    )
                    # Try to recover XML tool call from error body
                    recovered = _parse_xml_tool_call(str(e))
                    if recovered:
                        name, args = recovered
                        logger.info("Recovered XML tool call: %s %s", name, args)
                        # Return a synthetic-like structure via a simple namespace object
                        return _SyntheticToolResponse(name, args)

                    try:
                        return self._chat(
                            use_tools=False,
                            model=model,
                            provider=provider,
                            messages=messages,
                            temperature=0.5,
                            max_tokens=1024,
                        )
                    except Exception as e2:
                        if _is_rate_limit(e2):
                            last_error = e2
                            continue
                        last_error = e2
                        continue

                # Other 400s / errors — try next model
                status = getattr(e, "status_code", None)
                if status and 400 <= status < 500 and status != 401:
                    logger.warning("Client error %s on %s/%s: %s", status, provider, model, e)
                    last_error = e
                    continue
                raise

        if last_error and _is_rate_limit(last_error):
            raise last_error
        raise last_error or RuntimeError("All providers failed")

    async def _execute_tool(self, name: str, args: dict, user_id: int, chat_id: int) -> str:
        try:
            if name == "web_search":
                return web_search(args.get("query", ""), args.get("max_results", 5))
            elif name == "read_file":
                return read_file(user_id, args.get("filename", ""))
            elif name == "write_file":
                return write_file(
                    user_id, args.get("filename", ""), args.get("content", "")
                )
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
            for round_i in range(self.max_tool_rounds):
                try:
                    response = self._chat_with_fallback(messages, use_tools=True)
                except Exception as e:
                    if _is_rate_limit(e):
                        await memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                        return RATE_LIMIT_MSG
                    logger.exception("Chat error")
                    return f"عذراً، حدث خطأ في الخدمة. حاول مرة أخرى."

                # Synthetic recovery from XML tool call
                if isinstance(response, _SyntheticToolResponse):
                    result = await self._execute_tool(
                        response.name, response.args, user_id, chat_id
                    )
                    if len(result) > 2000:
                        result = result[:2000] + "\n...(مقطوع)"
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"(استدعاء أداة: {response.name})",
                        }
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": f"نتيجة الأداة {response.name}:\n{result}\n\nأجب على المستخدم بناءً على هذه النتيجة.",
                        }
                    )
                    continue

                msg = response.choices[0].message
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    reply = (msg.content or "").strip()
                    if not reply:
                        reply = "لم أتمكن من إنشاء رد. حاول صياغة السؤال differently."
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
                            for tc in tool_calls
                        ],
                    }
                )

                for tc in tool_calls:
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

        except Exception as e:
            if _is_rate_limit(e):
                await memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                return RATE_LIMIT_MSG
            logger.exception("Agent run error")
            return "عذراً، حدث خطأ غير متوقع. حاول مرة أخرى."


class _SyntheticToolResponse:
    """Minimal object when we recover a tool call from Groq XML error text."""

    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args or {}
