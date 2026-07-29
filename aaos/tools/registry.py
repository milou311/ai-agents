"""
Tool Manager — register, list OpenAI-compatible specs, invoke by name.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from aaos.tools.base import ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._specs: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: dict[str, Any],
    ) -> None:
        self._handlers[name] = handler
        self._specs[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }

    def list_specs(self) -> list[dict[str, Any]]:
        return list(self._specs.values())

    def has(self, name: str) -> bool:
        return name in self._handlers

    async def run(self, name: str, args: dict[str, Any], ctx: dict[str, Any]) -> str:
        handler = self._handlers.get(name)
        if not handler:
            return f"أداة غير معروفة: {name}"
        try:
            result = handler(args, ctx)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, ToolResult):
                return result.data if result.ok else (result.error or result.data)
            return str(result)
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return f"خطأ أثناء تنفيذ الأداة: {e}"


def build_default_registry() -> ToolRegistry:
    """Register built-in tools (legacy implementations via thin wrappers)."""
    from agents.tools.web_search import web_search
    from agents.tools.file_ops import read_file, write_file, list_files, delete_file
    from agents.tools.http_api import call_api
    from agents.tools.tasks_tool import manage_tasks, manage_reminders, manage_notes

    reg = ToolRegistry()

    reg.register(
        "web_search",
        lambda args, ctx: web_search(args.get("query", ""), args.get("max_results", 5)),
        "Search the internet for current information",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    )

    reg.register(
        "read_file",
        lambda args, ctx: read_file(int(ctx["user_id"]), args.get("filename", "")),
        "Read a saved user file",
        {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "File name"},
            },
            "required": ["filename"],
        },
    )

    reg.register(
        "write_file",
        lambda args, ctx: write_file(
            int(ctx["user_id"]), args.get("filename", ""), args.get("content", "")
        ),
        "Save content to a file",
        {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["filename", "content"],
        },
    )

    reg.register(
        "list_files",
        lambda args, ctx: list_files(int(ctx["user_id"])),
        "List saved files for the user",
        {"type": "object", "properties": {}},
    )

    reg.register(
        "delete_file",
        lambda args, ctx: delete_file(int(ctx["user_id"]), args.get("filename", "")),
        "Delete a saved file",
        {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
            },
            "required": ["filename"],
        },
    )

    async def _tasks(args, ctx):
        return await manage_tasks(
            int(ctx["user_id"]),
            action=args.get("action", "list"),
            title=args.get("title", ""),
            description=args.get("description", ""),
            due_date=args.get("due_date"),
            task_id=args.get("task_id"),
            status=args.get("status"),
        )

    reg.register(
        "manage_tasks",
        _tasks,
        "Manage tasks. action must be one of: add, list, complete, cancel",
        {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "add | list | complete | cancel"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "due_date": {"type": "string"},
                "task_id": {"type": "integer"},
            },
            "required": ["action"],
        },
    )

    async def _reminders(args, ctx):
        return await manage_reminders(
            int(ctx["user_id"]),
            int(ctx.get("chat_id") or ctx["user_id"]),
            action=args.get("action", "add"),
            message=args.get("message", ""),
            minutes_from_now=args.get("minutes_from_now", 0),
            remind_at=args.get("remind_at"),
        )

    reg.register(
        "manage_reminders",
        _reminders,
        "Set a reminder. action must be add",
        {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Must be: add"},
                "message": {"type": "string"},
                "minutes_from_now": {"type": "integer"},
            },
            "required": ["action", "message"],
        },
    )

    async def _notes(args, ctx):
        return await manage_notes(
            int(ctx["user_id"]),
            action=args.get("action", "list"),
            key=args.get("key", ""),
            value=args.get("value", ""),
        )

    reg.register(
        "manage_notes",
        _notes,
        "Permanent notes. action must be one of: set, get, list",
        {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "set | get | list"},
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["action"],
        },
    )

    reg.register(
        "call_api",
        lambda args, ctx: call_api(
            url=args.get("url", ""),
            method=args.get("method", "GET"),
            headers=args.get("headers"),
            body=args.get("body"),
        ),
        "Call an external HTTP API",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string", "description": "GET, POST, or PUT"},
            },
            "required": ["url"],
        },
    )

    return reg
