"""
Planner — produces a Plan. Never runs tools or mutates memory.

v1 strategy: heuristic + optional model assist for complex goals.
"""

from __future__ import annotations

import re
from typing import Optional

from aaos.planner.types import Plan, PlanStep

# Keywords that suggest tool use
_SEARCH = re.compile(
    r"(ابحث|بحث|search|google|أخبار|latest|من هو|what is|how to)",
    re.I,
)
_TASK = re.compile(r"(مهمة|مهام|task|todo|أضف مهمة|أكمل)", re.I)
_REMIND = re.compile(r"(ذكّر|ذكرني|تذكير|remind)", re.I)
_NOTE = re.compile(r"(احفظ ملاحظة|ملاحظة|remember that|note that)", re.I)
_FILE = re.compile(r"(ملف|اكتب في|احفظ في|read file|write file)", re.I)
_KNOW = re.compile(r"(في المعرفة|knowledge|من المستندات|حسب الملفات)", re.I)


class Planner:
    def plan(self, goal: str, context: Optional[dict] = None) -> Plan:
        goal = (goal or "").strip()
        if not goal:
            return Plan(goal="", steps=[], passthrough=True)

        steps: list[PlanStep] = []
        risk = "low"

        if _SEARCH.search(goal):
            steps.append(
                PlanStep(
                    id="s1",
                    action="tool",
                    description="Search the web",
                    tool="web_search",
                    args={"query": goal[:200]},
                )
            )
            risk = "medium"

        if _KNOW.search(goal):
            steps.append(
                PlanStep(
                    id="k1",
                    action="tool",
                    description="Search knowledge base",
                    tool="knowledge_search",
                    args={"query": goal[:200]},
                )
            )

        if _TASK.search(goal):
            steps.append(
                PlanStep(
                    id="t1",
                    action="tool",
                    description="Manage tasks (model will fill args)",
                    tool="manage_tasks",
                    args={"action": "list"},
                )
            )

        if _REMIND.search(goal):
            steps.append(
                PlanStep(
                    id="r1",
                    action="tool",
                    description="Set reminder (model fills details)",
                    tool="manage_reminders",
                    args={"action": "add", "message": goal[:120]},
                )
            )

        if _NOTE.search(goal):
            steps.append(
                PlanStep(
                    id="n1",
                    action="tool",
                    description="Save or read notes",
                    tool="manage_notes",
                    args={"action": "list"},
                )
            )

        if _FILE.search(goal):
            steps.append(
                PlanStep(
                    id="f1",
                    action="tool",
                    description="File operation",
                    tool="list_files",
                    args={},
                )
            )

        if not steps:
            return Plan(
                goal=goal,
                steps=[
                    PlanStep(
                        id="reply",
                        action="reply",
                        description="Direct answer without tools",
                    )
                ],
                passthrough=True,
                risk_level="low",
            )

        steps.append(
            PlanStep(
                id="final",
                action="reply",
                description="Synthesize answer for the user",
                depends_on=[s.id for s in steps],
            )
        )
        return Plan(goal=goal, steps=steps, risk_level=risk, passthrough=False)
