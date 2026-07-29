"""Model provider Protocol."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class ModelProvider(Protocol):
    name: str

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        **opts: Any,
    ) -> Any: ...
