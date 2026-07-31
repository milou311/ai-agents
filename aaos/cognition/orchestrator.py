"""
Cognition Orchestrator — wires ToT → plan context, Reflection → final reply,
and A2A partial results. Gemini-only (no other providers).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from aaos.cognition.a2a import get_a2a_bus
from aaos.cognition.reflection import Reflector, ReflectionResult
from aaos.cognition.tot import TreeOfThoughts, ToTResult
from aaos.config import get_settings
from aaos.models import ModelGateway
from aaos.monitoring import get_metrics
from aaos.planner import Planner

logger = logging.getLogger(__name__)


@dataclass
class CognitionBundle:
    tot: Optional[ToTResult] = None
    tot_context: str = ""
    reflection: Optional[ReflectionResult] = None
    final_text: str = ""


class CognitionOrchestrator:
    def __init__(self, gateway: Optional[ModelGateway] = None):
        self.settings = get_settings()
        self.gateway = gateway or ModelGateway()
        self.tot = TreeOfThoughts(self.gateway, width=3)
        self.reflector = Reflector(self.gateway)
        self.planner = Planner()
        self.bus = get_a2a_bus()

    def should_use_tot(self, user_message: str) -> bool:
        if not self.settings.enable_tot:
            return False
        plan = self.planner.plan(user_message)
        if plan.passthrough:
            return False
        return plan.risk_level in {"medium", "high"} or len(user_message) > 120

    def should_reflect(self, draft: str) -> bool:
        if not self.settings.enable_reflection:
            return False
        return len(draft or "") > 80

    def build_tot_context(self, user_message: str) -> str:
        if not self.should_use_tot(user_message):
            return ""
        try:
            result = self.tot.explore(user_message)
            get_metrics().inc("cognition.tot")
            # publish for peer agents
            self.bus.publish(
                sender="tot",
                topic="broadcast:plan",
                payload={
                    "best": result.best.summary if result.best else "",
                    "paths": len(result.paths),
                },
            )
            return self.tot.as_context(result)
        except Exception as e:
            logger.warning("ToT skip: %s", e)
            return ""

    def reflect_and_maybe_revise(self, goal: str, draft: str) -> tuple[str, ReflectionResult]:
        if not self.should_reflect(draft):
            return draft, ReflectionResult(ok=True, score=1.0, feedback="skip")
        try:
            ref = self.reflector.reflect(goal, draft)
            get_metrics().inc("cognition.reflection")
            text = ref.revised if ref.revised else draft
            if ref.revised:
                get_metrics().inc("cognition.reflection_revised")
            self.bus.publish(
                sender="reflector",
                topic="broadcast:reflection",
                payload={"score": ref.score, "ok": ref.ok, "feedback": ref.feedback[:200]},
            )
            return text, ref
        except Exception as e:
            logger.warning("Reflection skip: %s", e)
            return draft, ReflectionResult(ok=True, score=0.7, feedback=str(e))
