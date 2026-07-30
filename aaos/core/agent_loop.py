"""
AgentLoop — multi-step tool-calling runtime (lean path for latency).
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from aaos.config import get_settings
from aaos.identity import get_identity_manager
from aaos.memory import MemoryStore, get_default_store
from aaos.models import ModelGateway, ChatResult, SyntheticToolCall
from aaos.planner import Planner
from aaos.tools import ToolRegistry, build_default_registry
from aaos.monitoring import get_metrics, Timer

logger = logging.getLogger(__name__)

RATE_LIMIT_MSG = (
    "⏳ تم استهلاك الحصة الحالية من مزوّد الذكاء الاصطناعي.\n"
    "حاول بعد دقيقة، أو تأكد أن OPENAI_API_KEY مضاف كاحتياطي."
)


def _is_rate_limit(e: Exception) -> bool:
    if "RateLimit" in type(e).__name__:
        return True
    if getattr(e, "status_code", None) == 429:
        return True
    text = str(e).lower()
    return "rate limit" in text or "429" in text or "too many requests" in text


class AgentLoop:
    def __init__(
        self,
        gateway: Optional[ModelGateway] = None,
        memory: Optional[MemoryStore] = None,
        tools: Optional[ToolRegistry] = None,
        planner: Optional[Planner] = None,
    ):
        self.settings = get_settings()
        self.gateway = gateway or ModelGateway()
        self.memory = memory or get_default_store()
        self.tools = tools or build_default_registry()
        self.planner = planner or Planner()
        self.identity = get_identity_manager()

    def _system_prompt(self) -> str:
        return self.identity.system_prompt_block(include_runtime=False)

    async def run(
        self,
        user_id: int,
        chat_id: int,
        user_message: str,
        extra_context: str = "",
    ) -> str:
        metrics = get_metrics()
        metrics.inc("agent.requests")

        limit = self.settings.history_limit
        history = await self.memory.get_history(user_id, limit=limit)

        # Planner hint only for non-passthrough goals (saves tokens on small talk)
        plan = self.planner.plan(user_message)
        plan_hint = ""
        if not plan.passthrough and plan.steps:
            tools_hint = [
                s.tool for s in plan.steps if s.tool
            ][:4]
            if tools_hint:
                plan_hint = f"أدوات مرشّحة: {', '.join(tools_hint)}"

        messages: list[dict] = [{"role": "system", "content": self._system_prompt()}]
        if plan_hint:
            messages.append({"role": "system", "content": plan_hint[:200]})
        if extra_context:
            messages.append({"role": "system", "content": extra_context[:400]})
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        await self.memory.add_message(user_id, "user", user_message)

        ctx = {"user_id": user_id, "chat_id": chat_id}
        specs = self.tools.list_specs()

        try:
            with Timer("agent.loop_ms"):
                for _ in range(self.settings.max_tool_rounds):
                    try:
                        result = self.gateway.chat(
                            messages, tools=specs, use_tools=True
                        )
                    except Exception as e:
                        if _is_rate_limit(e):
                            await self.memory.add_message(
                                user_id, "assistant", RATE_LIMIT_MSG
                            )
                            metrics.inc("agent.rate_limited")
                            return RATE_LIMIT_MSG
                        logger.exception("Chat error")
                        return "عذراً، حدث خطأ في الخدمة. حاول مرة أخرى."

                    if isinstance(result, SyntheticToolCall):
                        tool_out = await self.tools.run(
                            result.name, result.arguments, ctx
                        )
                        if len(tool_out) > 1500:
                            tool_out = tool_out[:1500] + "\n...(مقطوع)"
                        messages.append(
                            {
                                "role": "assistant",
                                "content": f"(tool: {result.name})",
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"نتيجة {result.name}:\n{tool_out}\n\n"
                                    "أجب المستخدم باختصار."
                                ),
                            }
                        )
                        continue

                    assert isinstance(result, ChatResult)

                    if not result.tool_calls:
                        reply = (
                            result.content
                            or "لم أتمكن من إنشاء رد. حاول إعادة صياغة السؤال."
                        )
                        await self.memory.add_message(user_id, "assistant", reply)
                        metrics.inc("agent.ok")
                        return reply

                    messages.append(
                        {
                            "role": "assistant",
                            "content": result.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.name,
                                        "arguments": json.dumps(
                                            tc.arguments, ensure_ascii=False
                                        ),
                                    },
                                }
                                for tc in result.tool_calls
                            ],
                        }
                    )

                    for tc in result.tool_calls:
                        tool_out = await self.tools.run(tc.name, tc.arguments, ctx)
                        if len(tool_out) > 1500:
                            tool_out = tool_out[:1500] + "\n...(مقطوع)"
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_out,
                            }
                        )

            final = "أنجزت أكبر عدد ممكن من الخطوات. حاول تقسيم الطلب إن أمكن."
            await self.memory.add_message(user_id, "assistant", final)
            return final

        except Exception as e:
            if _is_rate_limit(e):
                await self.memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                return RATE_LIMIT_MSG
            logger.exception("AgentLoop error")
            return "عذراً، حدث خطأ غير متوقع. حاول مرة أخرى."
