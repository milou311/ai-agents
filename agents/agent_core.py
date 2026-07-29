"""
Legacy AgentCore — thin adapter over aaos.core.AgentLoop.

Telegram and other callers keep importing agents.agent_core.AgentCore.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aaos.core.agent_loop import AgentLoop


class AgentCore:
    """Backward-compatible facade."""

    def __init__(self):
        self._loop = AgentLoop()

    async def run(
        self,
        user_id: int,
        chat_id: int,
        user_message: str,
        extra_context: str = "",
    ) -> str:
        return await self._loop.run(
            user_id=user_id,
            chat_id=chat_id,
            user_message=user_message,
            extra_context=extra_context,
        )
