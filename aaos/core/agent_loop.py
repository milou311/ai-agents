"""AgentLoop — Gemini via ModelGateway; local replies for identity/greetings."""

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
    "⏳ حصة Gemini منتهية مؤقتاً.\n"
    "انتظر قليلاً أو تحقق من المفتاح في Render (GEMINI_API_KEY)."
)

_IDENTITY_RE = re.compile(
    r"(من\s*أنت|من\s*انت|من\s*انا|من\s*أنا|عرف\s*نفسك|"
    r"who\s*are\s*you|ما\s*اسمك|من\s*هو\s*ops)",
    re.I,
)
_TRIVIAL = re.compile(
    r"^\s*(مرحبا|مرحباً|السلام\s*عليكم|سلام|هلا|اهلا|أهلا|هاي|هلو|"
    r"hi|hello|hey|حسنا|حسناً|تمام|اوكي|أوكي|ok|okay|"
    r"شكرا|شكراً|thanks|نعم|لا)\s*[!.؟?]*\s*$",
    re.I,
)


def _is_rate_limit(e: Exception) -> bool:
    text = str(e).lower()
    return any(
        x in text
        for x in ("rate limit", "429", "resource_exhausted", "quota", "cooldown", "فترة انتظار")
    )


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
        if _IDENTITY_RE.search(text):
            return self.identity.introduce("ar")
        if _TRIVIAL.match(text):
            low = text.lower()
            if re.search(r"شكرا|thanks", low):
                return "العفو 👍"
            if re.search(r"^(حسنا|حسناً|تمام|اوكي|أوكي|ok|okay|نعم)\b", low):
                return "تمام، أنا هنا. ماذا تحتاج؟"
            if re.search(r"^لا\b", low):
                return "حسنًا. إذا احتجت شيئاً أنا موجود."
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

        local = self._local_reply(user_message)
        if local:
            await self.memory.add_message(user_id, "user", user_message)
            await self.memory.add_message(user_id, "assistant", local)
            metrics.inc("agent.local_reply")
            self.ops.end_goal(goal_id, ok=True)
            return local

        history = await self.memory.get_history(
            user_id, limit=self.settings.history_limit
        )
        plan = self.planner.plan(user_message)
        plan_hint = ""
        if not plan.passthrough and plan.steps:
            tools_hint = [s.tool for s in plan.steps if s.tool][:4]
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
                            self.ops.record_error("rate_limit", str(e))
                            await self.memory.add_message(
                                user_id, "assistant", RATE_LIMIT_MSG
                            )
                            self.ops.end_goal(goal_id, ok=False)
                            return RATE_LIMIT_MSG
                        logger.exception("Chat error")
                        self.ops.record_error("chat", str(e))
                        self.ops.end_goal(goal_id, ok=False)
                        return f"عذراً، حدث خطأ: {e}"

                    if isinstance(result, SyntheticToolCall):
                        tool_out = await self.tools.run(
                            result.name, result.arguments, ctx
                        )
                        self.ops.record_tool(
                            result.name, not str(tool_out).startswith("خطأ")
                        )
                        if len(tool_out) > 1500:
                            tool_out = tool_out[:1500] + "\n...(مقطوع)"
                        messages.append(
                            {"role": "assistant", "content": f"(tool: {result.name})"}
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": f"نتيجة {result.name}:\n{tool_out}\n\nأجب باختصار.",
                            }
                        )
                        continue

                    assert isinstance(result, ChatResult)
                    if not result.tool_calls:
                        reply = result.content or "لم أتمكن من إنشاء رد."
                        await self.memory.add_message(user_id, "assistant", reply)
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
                        self.ops.record_tool(
                            tc.name, not str(tool_out).startswith("خطأ")
                        )
                        if len(tool_out) > 1500:
                            tool_out = tool_out[:1500] + "\n...(مقطوع)"
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_out,
                            }
                        )

            final = "أنجزت أكبر عدد ممكن من الخطوات."
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
            return "عذراً، حدث خطأ غير متوقع."
