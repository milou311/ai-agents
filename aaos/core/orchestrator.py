"""
Core Orchestrator.

Depends only on Interfaces (Protocols), never on concrete SDKs.
Phase 0: thin wrapper that can delegate to legacy agent until migration completes.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

from aaos.core.types import AgentRequest, AgentResponse

logger = logging.getLogger(__name__)


class ModelGateway(Protocol):
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        **opts: Any,
    ) -> Any: ...


class MemoryGateway(Protocol):
    async def get_history(self, user_id: str, limit: int = 8) -> list[dict[str, str]]: ...

    async def add_message(self, user_id: str, role: str, content: str) -> None: ...


class ToolGateway(Protocol):
    def list_specs(self) -> list[dict[str, Any]]: ...

    async def run(self, name: str, args: dict[str, Any], ctx: dict[str, Any]) -> str: ...


class Orchestrator:
    """
    Central request lifecycle.

    Phase 0 implementation may inject a legacy runner callable while
    Models/Memory/Tools are migrated module-by-module.
    """

    def __init__(
        self,
        memory: Optional[MemoryGateway] = None,
        models: Optional[ModelGateway] = None,
        tools: Optional[ToolGateway] = None,
        legacy_runner: Optional[Any] = None,
    ):
        self.memory = memory
        self.models = models
        self.tools = tools
        self.legacy_runner = legacy_runner

    async def run(self, request: AgentRequest) -> AgentResponse:
        try:
            if self.legacy_runner is not None:
                text = await self.legacy_runner(
                    user_id=int(request.user_id) if request.user_id.isdigit() else 0,
                    chat_id=int(request.chat_id or request.user_id)
                    if (request.chat_id or request.user_id).isdigit()
                    else 0,
                    user_message=request.text,
                )
                return AgentResponse(request_id=request.request_id, text=text or "")

            return AgentResponse(
                request_id=request.request_id,
                text=(
                    "AAOS Core is initialized, but Models/Memory/Tools "
                    "are not wired yet. Complete Phase 1 migration."
                ),
                error="not_wired",
            )
        except Exception as e:
            logger.exception("Orchestrator failure")
            return AgentResponse(
                request_id=request.request_id,
                text="عذراً، حدث خطأ غير متوقع. حاول مرة أخرى.",
                error=str(e),
            )
