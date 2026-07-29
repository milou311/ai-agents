"""Skill graphs — reusable multi-step procedures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SkillStep:
    name: str
    tool: Optional[str] = None
    args_template: dict[str, Any] = field(default_factory=dict)
    prompt: str = ""


@dataclass
class Skill:
    name: str
    description: str
    steps: list[SkillStep] = field(default_factory=list)


# Built-in example skills (data-driven)
RESEARCH_SKILL = Skill(
    name="research_topic",
    description="Search web + knowledge then summarize",
    steps=[
        SkillStep(name="web", tool="web_search", args_template={"query": "{topic}"}),
        SkillStep(
            name="kb", tool="knowledge_search", args_template={"query": "{topic}"}
        ),
        SkillStep(name="summarize", prompt="Summarize findings for the user"),
    ],
)

SKILLS: dict[str, Skill] = {
    RESEARCH_SKILL.name: RESEARCH_SKILL,
}


def get_skill(name: str) -> Optional[Skill]:
    return SKILLS.get(name)
