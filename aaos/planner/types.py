"""Plan data structures — Planner never executes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlanStep:
    id: str
    action: str  # reply | tool | think
    description: str = ""
    tool: Optional[str] = None
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    risk_level: str = "low"  # low | medium | high
    passthrough: bool = False  # True = single direct reply, no forced tools
