"""Model layer result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResult:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    raw: Any = None


@dataclass
class SyntheticToolCall:
    """Recovered from provider malformed tool XML (e.g. Groq tool_use_failed)."""

    name: str
    arguments: dict[str, Any]
