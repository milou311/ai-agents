"""
Multi-agent Supervisor scaffold.

Routes goals to specialist profiles (same AgentLoop, different system hints).
Full parallel agents come later; this is the coordination surface.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from aaos.core.agent_loop import AgentLoop

logger = logging.getLogger(__name__)


@dataclass
class AgentProfile:
    name: str
    system_hint: str
    match: re.Pattern


PROFILES = [
    AgentProfile(
        name="research",
        system_hint="Focus on research: use web_search and knowledge_search before answering.",
        match=re.compile(r"(ابحث|بحث|research|analyze|حلّل)", re.I),
    ),
    AgentProfile(
        name="ops",
        system_hint="Focus on tasks, reminders, and notes management tools.",
        match=re.compile(r"(مهمة|تذكير|ملاحظة|task|remind|todo)", re.I),
    ),
    AgentProfile(
        name="general",
        system_hint="General assistant.",
        match=re.compile(r".*", re.I),
    ),
]


class Supervisor:
    def __init__(self, loop: Optional[AgentLoop] = None):
        self.loop = loop or AgentLoop()

    def select_profile(self, text: str) -> AgentProfile:
        for p in PROFILES:
            if p.name == "general":
                continue
            if p.match.search(text or ""):
                return p
        return PROFILES[-1]

    async def run(self, user_id: int, chat_id: int, text: str) -> str:
        profile = self.select_profile(text)
        logger.info("Supervisor routed to profile=%s", profile.name)
        return await self.loop.run(
            user_id,
            chat_id,
            text,
            extra_context=f"[agent_profile={profile.name}] {profile.system_hint}",
        )
