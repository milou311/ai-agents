"""
Unified Model Gateway — provider-agnostic chat with failover.

Core and Planner depend on this module, never on groq/openai SDKs directly.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from aaos.config import get_settings
from aaos.models.types import ChatResult, SyntheticToolCall, ToolCall

logger = logging.getLogger(__name__)


def _is_rate_limit(e: Exception) -> bool:
    if "RateLimit" in type(e).__name__:
        return True
    if getattr(e, "status_code", None) == 429:
        return True
    return False


def _is_tool_use_failed(e: Exception) -> bool:
    if getattr(e, "status_code", None) != 400:
        return False
    text = str(e).lower()
    return "tool_use_failed" in text or "failed to call a function" in text


def _parse_xml_tool_call(text: str) -> Optional[tuple[str, dict]]:
    if not text:
        return None
    patterns = [
        r"<function=([a-zA-Z0-9_]+)\s*(\{.*?\})\s*</function>",
        r"<function=([a-zA-Z0-9_]+)>\s*(\{.*?\})\s*</function>",
        r"<function=([a-zA-Z0-9_]+)\s*(\{[^<]*\})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL)
        if m:
            name = m.group(1).strip()
            try:
                args = json.loads(m.group(2))
            except json.JSONDecodeError:
                args = {}
            return name, args
    return None


def _normalize_message(msg: Any, model: str, provider: str) -> ChatResult:
    content = (getattr(msg, "content", None) or "") or ""
    tool_calls: list[ToolCall] = []
    raw_tcs = getattr(msg, "tool_calls", None) or []
    for i, tc in enumerate(raw_tcs):
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", "") if fn else ""
        arguments_raw = getattr(fn, "arguments", "{}") if fn else "{}"
        try:
            args = json.loads(arguments_raw or "{}")
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(
            ToolCall(
                id=getattr(tc, "id", f"call_{i}"),
                name=name,
                arguments=args,
            )
        )
    return ChatResult(
        content=content.strip(),
        tool_calls=tool_calls,
        model=model,
        provider=provider,
        raw=msg,
    )


class ModelGateway:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self._groq = None
        self._openai = None

        if settings.groq_api_key:
            try:
                from groq import Groq

                self._groq = Groq(api_key=settings.groq_api_key)
            except Exception as e:
                logger.warning("Groq init failed: %s", e)

        if settings.openai_api_key:
            try:
                from openai import OpenAI

                self._openai = OpenAI(api_key=settings.openai_api_key)
            except Exception as e:
                logger.warning("OpenAI init failed: %s", e)

    def _chain(self) -> list[tuple[str, str]]:
        """Return (model, provider) pairs in failover order."""
        chain: list[tuple[str, str]] = []
        primary = self.settings.primary_model
        # Primary always tried on Groq if available
        if self._groq:
            chain.append((primary, "groq"))
            for m in self.settings.fallback_models:
                if m.startswith("gpt-"):
                    continue
                if m != primary:
                    chain.append((m, "groq"))
        if self._openai:
            for m in self.settings.fallback_models:
                if m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3"):
                    chain.append((m, "openai"))
            if not any(p == "openai" for _, p in chain):
                chain.append(("gpt-4o-mini", "openai"))
        return chain

    def _create(
        self,
        *,
        provider: str,
        model: str,
        messages: list[dict],
        tools: Optional[list] = None,
        use_tools: bool = True,
    ):
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": self.settings.max_tokens,
        }
        if use_tools and tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        if provider == "groq":
            if not self._groq:
                raise RuntimeError("Groq not configured")
            return self._groq.chat.completions.create(**kwargs)
        if provider == "openai":
            if not self._openai:
                raise RuntimeError("OpenAI not configured")
            return self._openai.chat.completions.create(**kwargs)
        raise RuntimeError(f"Unknown provider: {provider}")

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        use_tools: bool = True,
    ) -> ChatResult | SyntheticToolCall:
        last_error: Exception | None = None
        chain = self._chain()
        if not chain:
            raise RuntimeError("No model providers configured")

        for model, provider in chain:
            try:
                resp = self._create(
                    provider=provider,
                    model=model,
                    messages=messages,
                    tools=tools,
                    use_tools=use_tools and bool(tools),
                )
                msg = resp.choices[0].message
                return _normalize_message(msg, model, provider)
            except Exception as e:
                if _is_rate_limit(e):
                    logger.warning("Rate limit %s/%s", provider, model)
                    last_error = e
                    time.sleep(0.3)
                    continue

                if use_tools and _is_tool_use_failed(e):
                    logger.warning("tool_use_failed %s/%s", provider, model)
                    recovered = _parse_xml_tool_call(str(e))
                    if recovered:
                        name, args = recovered
                        return SyntheticToolCall(name=name, arguments=args)
                    try:
                        resp = self._create(
                            provider=provider,
                            model=model,
                            messages=messages,
                            tools=None,
                            use_tools=False,
                        )
                        msg = resp.choices[0].message
                        return _normalize_message(msg, model, provider)
                    except Exception as e2:
                        last_error = e2
                        continue

                status = getattr(e, "status_code", None)
                if status and 400 <= status < 500 and status != 401:
                    logger.warning("Client error %s on %s/%s: %s", status, provider, model, e)
                    last_error = e
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError("All model providers failed")
