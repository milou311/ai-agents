"""
Executor — runs Plan steps via ToolRegistry (side effects allowed here).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from aaos.planner.types import Plan
from aaos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    step_id: str
    ok: bool
    output: str = ""


@dataclass
class ExecutionResult:
    goal: str
    steps: list[StepResult] = field(default_factory=list)
    final_text: str = ""


class Executor:
    def __init__(self, tools: ToolRegistry):
        self.tools = tools

    async def execute(self, plan: Plan, ctx: dict[str, Any]) -> ExecutionResult:
        results: list[StepResult] = []
        for step in plan.steps:
            if step.action == "reply":
                results.append(
                    StepResult(step_id=step.id, ok=True, output=step.description)
                )
                continue
            if step.action == "tool" and step.tool:
                out = await self.tools.run(step.tool, step.args or {}, ctx)
                results.append(StepResult(step_id=step.id, ok=True, output=out))
            else:
                results.append(
                    StepResult(
                        step_id=step.id, ok=False, output=f"unsupported action {step.action}"
                    )
                )
        final = "\n".join(f"[{r.step_id}] {r.output[:500]}" for r in results)
        return ExecutionResult(goal=plan.goal, steps=results, final_text=final)
