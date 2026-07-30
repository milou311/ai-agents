"""
Multi-agent Supervisor + A2A partial-result exchange.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from aaos.cognition.a2a import get_a2a_bus
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
        self.bus = get_a2a_bus()

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

        # A2A: announce assignment (other agents can react without Supervisor)
        self.bus.publish(
            sender="supervisor",
            topic="broadcast:assignment",
            payload={
                "agent": profile.name,
                "user_id": user_id,
                "goal": text[:300],
            },
        )

        # Pull any pending partial results for this specialist
        pending = self.bus.receive(profile.name, max_messages=5)
        extra_parts = [
            f"[A2A from {m.sender}] {m.payload}" for m in pending
        ]
        extra = f"[agent_profile={profile.name}] {profile.system_hint}"
        if extra_parts:
            extra += "\n" + "\n".join(extra_parts)[:400]

        reply = await self.loop.run(
            user_id,
            chat_id,
            text,
            extra_context=extra,
        )

        # Publish partial/final for peers
        self.bus.send(
            sender=profile.name,
            to_agent="supervisor",
            payload={"status": "done", "preview": (reply or "")[:200]},
        )
        self.bus.publish(
            sender=profile.name,
            topic="broadcast:result",
            payload={
                "agent": profile.name,
                "preview": (reply or "")[:200],
            },
        )
        return reply
