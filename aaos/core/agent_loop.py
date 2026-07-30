"""
AgentLoop — tool-calling runtime with optional ToT + Reflection + Self-State.

Identity/greeting questions answered locally (no LLM) so the bot still works
when providers are rate-limited.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Optional

from aaos.config import get_settings
from aaos.cognition import Reflector, TreeOfThoughts
from aaos.identity import get_identity_manager
from aaos.identity.state import get_operational_state
from aaos.memory import MemoryStore, get_default_store
from aaos.models import ModelGateway, ChatResult, SyntheticToolCall
from aaos.planner import Planner
from aaos.tools import ToolRegistry, build_default_registry
from aaos.monitoring import get_metrics, Timer

logger = logging.getLogger(__name__)

RATE_LIMIT_MSG = (
    "⏳ تم استهلاك الحصة الحالية من مزوّد الذكاء الاصطناعي.\n"
    "أضف OPENAI_API_KEY في Render كاحتياطي، أو انتظر تجدد حصة Groq.\n"
    "الأسئلة عن هويتي تعمل دائماً بدون نموذج."
)

_IDENTITY_RE = re.compile(
    r"(^|\s)(من\s*أنت|من\s*انت|من\s*أنتم|عرف\s*نفسك|عرفيني|من\s*هو\s*ops|"
    r"who\s*are\s*you|what\s*are\s*you|your\s*name|ما\s*اسمك)(\s|$|[؟?!.])",
    re.I,
)
_GREET_RE = re.compile(
    r"^(مرحبا|مرحباً|السلام|سلام|هلا|اهلا|أهلا|hi|hello|hey)\b",
    re.I,
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
        self.reflector = Reflector(self.gateway)
        self.tot = TreeOfThoughts(self.gateway, width=3)
        self.ops = get_operational_state()

    def _system_prompt(self) -> str:
        return self.identity.system_prompt_block(include_runtime=False)

    def _local_reply(self, user_message: str) -> Optional[str]:
        text = (user_message or "").strip()
        if not text:
            return None
        if _IDENTITY_RE.search(text) or text in {"من انا ؟", "من انا؟", "من أنا؟", "من أنا ؟"}:
            # User often types "من انا" meaning who are you in dialect
            return self.identity.introduce("ar")
        if _GREET_RE.search(text) and len(text) < 40:
            return self.identity.introduce("ar")
        return None

    async def run(
        self,
        user_id: int,
        chat_id: int,
        user_message: str,
        extra_context: str = "",
    ) -> str:
        metrics = get_metrics()
        metrics.inc("agent.requests")
        goal_id = str(uuid.uuid4())
        self.ops.start_goal(goal_id, user_message, user_id=user_id)

        # Fast path: no LLM needed
        local = self._local_reply(user_message)
        if local:
            await self.memory.add_message(user_id, "user", user_message)
            await self.memory.add_message(user_id, "assistant", local)
            metrics.inc("agent.local_reply")
            self.ops.end_goal(goal_id, ok=True)
            return local

        limit = self.settings.history_limit
        history = await self.memory.get_history(user_id, limit=limit)

        plan = self.planner.plan(user_message)
        plan_hint = ""
        if not plan.passthrough and plan.steps:
            tools_hint = [s.tool for s in plan.steps if s.tool][:4]
            if tools_hint:
                plan_hint = f"أدوات مرشّحة: {', '.join(tools_hint)}"

        tot_ctx = ""
        use_tot = (
            getattr(self.settings, "enable_tot", False)
            and not plan.passthrough
            and plan.risk_level in {"medium", "high"}
        )
        if use_tot:
            try:
                tot_result = self.tot.explore(user_message)
                tot_ctx = self.tot.as_context(tot_result)
                metrics.inc("cognition.tot")
            except Exception as e:
                self.ops.record_error("tot", str(e))

        messages: list[dict] = [{"role": "system", "content": self._system_prompt()}]
        if plan_hint:
            messages.append({"role": "system", "content": plan_hint[:200]})
        if tot_ctx:
            messages.append({"role": "system", "content": tot_ctx})
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
                            self.ops.record_error("rate_limit", str(e))
                            await self.memory.add_message(
                                user_id, "assistant", RATE_LIMIT_MSG
                            )
                            metrics.inc("agent.rate_limited")
                            self.ops.end_goal(goal_id, ok=False)
                            return RATE_LIMIT_MSG
                        logger.exception("Chat error")
                        self.ops.record_error("chat", str(e))
                        self.ops.end_goal(goal_id, ok=False)
                        return "عذراً، حدث خطأ في الخدمة. حاول مرة أخرى."

                    if isinstance(result, SyntheticToolCall):
                        tool_out = await self.tools.run(
                            result.name, result.arguments, ctx
                        )
                        ok = not tool_out.startswith("خطأ")
                        self.ops.record_tool(result.name, ok)
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
                        if getattr(self.settings, "enable_reflection", False) and len(
                            reply
                        ) > 80:
                            try:
                                ref = self.reflector.reflect(user_message, reply)
                                metrics.inc("cognition.reflection")
                                if ref.revised:
                                    reply = ref.revised
                                    metrics.inc("cognition.reflection_revised")
                            except Exception as e:
                                self.ops.record_error("reflection", str(e))

                        await self.memory.add_message(user_id, "assistant", reply)
                        metrics.inc("agent.ok")
                        self.ops.end_goal(goal_id, ok=True)
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
                        ok = not str(tool_out).startswith("خطأ")
                        self.ops.record_tool(tc.name, ok)
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
            self.ops.end_goal(goal_id, ok=False)
            return final

        except Exception as e:
            if _is_rate_limit(e):
                await self.memory.add_message(user_id, "assistant", RATE_LIMIT_MSG)
                self.ops.end_goal(goal_id, ok=False)
                return RATE_LIMIT_MSG
            logger.exception("AgentLoop error")
            self.ops.record_error("agent_loop", str(e))
            self.ops.end_goal(goal_id, ok=False)
            return "عذراً، حدث خطأ غير متوقع. حاول مرة أخرى."
