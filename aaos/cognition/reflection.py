"""
Self-Reflection — evaluate draft answer against the user goal before delivery.

Not consciousness: a second model pass that scores adequacy and may revise.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from aaos.models import ModelGateway, ChatResult

logger = logging.getLogger(__name__)


@dataclass
class ReflectionResult:
    ok: bool
    score: float  # 0..1
    feedback: str
    revised: Optional[str] = None


class Reflector:
    def __init__(self, gateway: Optional[ModelGateway] = None):
        self.gateway = gateway or ModelGateway()

    def reflect(self, goal: str, draft: str) -> ReflectionResult:
        if not draft or not goal:
            return ReflectionResult(ok=True, score=1.0, feedback="empty skip")

        # Cheap heuristic gate — skip LLM reflection for very short OK replies
        if len(draft) < 40 and not any(
            x in draft for x in ("خطأ", "عذراً", "لا أعرف", "error")
        ):
            return ReflectionResult(ok=True, score=0.85, feedback="short_ok")

        prompt = (
            "Evaluate whether the DRAFT fully answers the GOAL.\n"
            "Reply ONLY JSON: {\"score\":0.0-1.0,\"ok\":true/false,"
            "\"feedback\":\"...\",\"revised\":null or improved answer}\n"
            f"GOAL:\n{goal[:800]}\n\nDRAFT:\n{draft[:3000]}\n"
        )
        try:
            result = self.gateway.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict QA critic for an AI assistant. "
                            "Be concise. Prefer ok=true if the draft is adequate."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                tools=None,
                use_tools=False,
            )
            text = result.content if isinstance(result, ChatResult) else str(result)
            data = _extract_json(text)
            if not data:
                return ReflectionResult(ok=True, score=0.7, feedback="parse_fail")
            score = float(data.get("score", 0.7))
            ok = bool(data.get("ok", score >= 0.6))
            feedback = str(data.get("feedback", ""))[:500]
            revised = data.get("revised")
            if revised is not None:
                revised = str(revised).strip() or None
            # Only replace if critic is confident and score low
            if ok or score >= 0.6:
                revised = None
            return ReflectionResult(
                ok=ok or score >= 0.6, score=score, feedback=feedback, revised=revised
            )
        except Exception as e:
            logger.warning("Reflection failed: %s", e)
            return ReflectionResult(ok=True, score=0.7, feedback=f"skip:{e}")


def _extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
