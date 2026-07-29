"""Run a Skill by executing tool steps then asking the model to synthesize."""

from __future__ import annotations

import logging
from typing import Any

from aaos.models import ModelGateway
from aaos.skills.base import Skill, get_skill
from aaos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class SkillRunner:
    def __init__(self, tools: ToolRegistry, gateway: ModelGateway | None = None):
        self.tools = tools
        self.gateway = gateway or ModelGateway()

    async def run(
        self, skill_name: str, variables: dict[str, Any], ctx: dict[str, Any]
    ) -> str:
        skill = get_skill(skill_name)
        if not skill:
            return f"المهارة غير موجودة: {skill_name}"

        collected: list[str] = []
        for step in skill.steps:
            if step.tool:
                args = {
                    k: (v.format(**variables) if isinstance(v, str) else v)
                    for k, v in (step.args_template or {}).items()
                }
                out = await self.tools.run(step.tool, args, ctx)
                collected.append(f"[{step.name}/{step.tool}] {out[:1500]}")
            elif step.prompt:
                collected.append(f"[{step.name}] prompt:{step.prompt}")

        bundle = "\n\n".join(collected)
        messages = [
            {
                "role": "system",
                "content": (
                    f"You completed skill '{skill.name}'. "
                    "Summarize results clearly for the end user in their language."
                ),
            },
            {"role": "user", "content": bundle[:6000]},
        ]
        try:
            result = self.gateway.chat(messages, tools=None, use_tools=False)
            from aaos.models import ChatResult

            if isinstance(result, ChatResult):
                return result.content or bundle[:2000]
            return bundle[:2000]
        except Exception as e:
            logger.exception("Skill synthesize failed")
            return bundle[:2000] + f"\n(synthesis error: {e})"
