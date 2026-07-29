"""Tool contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class ToolResult:
    ok: bool
    data: str
    error: Optional[str] = None


@runtime_checkable
class Tool(Protocol):
    name: str

    def spec(self) -> dict[str, Any]: ...

    async def run(self, args: dict[str, Any], ctx: dict[str, Any]) -> ToolResult: ...
