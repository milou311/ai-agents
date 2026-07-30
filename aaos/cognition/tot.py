"""
Tree of Thoughts (lightweight).

Generate multiple candidate approaches, score them, return the best path.
Does not replace Executor — feeds a chosen strategy into the agent loop context.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from aaos.models import ModelGateway, ChatResult

logger = logging.getLogger(__name__)


@dataclass
class ThoughtPath:
    id: str
    summary: str
    steps: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class ToTResult:
    paths: list[ThoughtPath]
    best: Optional[ThoughtPath]


class TreeOfThoughts:
    def __init__(self, gateway: Optional[ModelGateway] = None, width: int = 3):
        self.gateway = gateway or ModelGateway()
        self.width = width

    def explore(self, goal: str) -> ToTResult:
        goal = (goal or "").strip()
        if not goal:
            return ToTResult(paths=[], best=None)

        prompt = (
            f"Propose {self.width} distinct strategies to achieve the GOAL.\n"
            "Return ONLY JSON list: "
            '[{"id":"p1","summary":"...","steps":["..."],"score":0.0-1.0}, ...]\n'
            f"GOAL: {goal[:1000]}"
        )
        try:
            result = self.gateway.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a planning module. Diversify strategies. "
                            "Higher score = more promising given constraints."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                tools=None,
                use_tools=False,
            )
            text = result.content if isinstance(result, ChatResult) else str(result)
            items = _extract_list(text)
            paths: list[ThoughtPath] = []
            for i, it in enumerate(items[: self.width]):
                paths.append(
                    ThoughtPath(
                        id=str(it.get("id") or f"p{i+1}"),
                        summary=str(it.get("summary") or "")[:300],
                        steps=[str(s)[:200] for s in (it.get("steps") or [])][:6],
                        score=float(it.get("score") or 0.5),
                    )
                )
            if not paths:
                paths = [
                    ThoughtPath(
                        id="p1",
                        summary="Direct answer / single-path",
                        steps=["Answer the user directly using tools if needed"],
                        score=0.5,
                    )
                ]
            paths.sort(key=lambda p: -p.score)
            return ToTResult(paths=paths, best=paths[0])
        except Exception as e:
            logger.warning("ToT failed: %s", e)
            fallback = ThoughtPath(
                id="p1",
                summary="Fallback direct path",
                steps=["Use tools if needed and answer"],
                score=0.5,
            )
            return ToTResult(paths=[fallback], best=fallback)

    def as_context(self, result: ToTResult) -> str:
        if not result.best:
            return ""
        b = result.best
        steps = " → ".join(b.steps) if b.steps else b.summary
        alts = len(result.paths)
        return (
            f"Tree-of-Thoughts: chose {b.id} (score={b.score:.2f}) "
            f"among {alts} paths. Strategy: {b.summary}. Steps: {steps}"
        )[:600]


def _extract_list(text: str) -> list[dict]:
    text = (text or "").strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "paths" in data:
            return data["paths"]
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return []
    return []
