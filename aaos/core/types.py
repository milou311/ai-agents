"""Shared core types (Interface contracts)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentRequest:
    request_id: str
    user_id: str
    channel: str  # telegram | cli | api | web
    text: str
    chat_id: Optional[str] = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    request_id: str
    text: str
    attachments: list[dict[str, Any]] = field(default_factory=list)
    tool_traces: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
