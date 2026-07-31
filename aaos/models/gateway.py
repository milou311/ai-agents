"""
Unified Model Gateway.

Priority:
  1) Google Gemini (GEMINI_API_KEY / GOOGLE_API_KEY) — free tier friendly
  2) Groq (GROQ_API_KEY) — optional
  3) OpenAI (OPENAI_API_KEY) — optional

On 429: skip provider immediately (cooldown), try next.
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

_provider_cooldown_until: dict[str, float] = {}


def _is_rate_limit(e: Exception) -> bool:
    if "RateLimit" in type(e).__name__:
        return True
    if getattr(e, "status_code", None) == 429:
        return True
    text = str(e).lower()
    return any(
        x in text
        for x in (
            "rate limit",
            "too many requests",
            "429",
            "resource_exhausted",
            "quota",
        )
    )


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


def _normalize_openai_style(msg: Any, model: str, provider: str) -> ChatResult:
    content = (getattr(msg, "content", None) or "") or ""
    tool_calls: list[ToolCall] = []
    for i, tc in enumerate(getattr(msg, "tool_calls", None) or []):
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", "") if fn else ""
        raw_args = getattr(fn, "arguments", "{}") if fn else "{}"
        try:
            args = json.loads(raw_args or "{}")
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(
            ToolCall(id=getattr(tc, "id", f"call_{i}"), name=name, arguments=args)
        )
    return ChatResult(
        content=content.strip(),
        tool_calls=tool_calls,
        model=model,
        provider=provider,
        raw=msg,
    )


def _messages_to_gemini_contents(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Split system text; map roles to Gemini user/model turns."""
    system_parts: list[str] = []
    contents: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role == "system":
            system_parts.append(str(content))
            continue
        if role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": f"[tool result]\n{content}"}],
                }
            )
            continue
        if role == "assistant":
            # Include tool call summary if present
            extra = ""
            tcs = m.get("tool_calls") or []
            if tcs:
                names = []
                for tc in tcs:
                    fn = tc.get("function") or {}
                    names.append(fn.get("name", "tool"))
                extra = f"\n[calling tools: {', '.join(names)}]"
            contents.append(
                {"role": "model", "parts": [{"text": str(content) + extra}]}
            )
            continue
        # user
        contents.append({"role": "user", "parts": [{"text": str(content)}]})
    system = "\n".join(system_parts) if system_parts else None
    if not contents:
        contents = [{"role": "user", "parts": [{"text": "."}]}]
    return system, contents


def _openai_tools_to_gemini_declaration(tools: list[dict]) -> list[dict]:
    decls = []
    for t in tools or []:
        fn = t.get("function") or {}
        name = fn.get("name")
        if not name:
            continue
        decls.append(
            {
                "name": name,
                "description": fn.get("description") or name,
                "parameters": fn.get("parameters")
                or {"type": "object", "properties": {}},
            }
        )
    return decls


class ModelGateway:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self._gemini = None
        self._groq = None
        self._openai = None

        gemini_key = settings.gemini_api_key
        if gemini_key:
            try:
                from google import genai

                self._gemini = genai.Client(api_key=gemini_key)
                logger.info("Gemini client ready")
            except Exception as e:
                logger.warning("Gemini init failed: %s", e)

        if settings.groq_api_key:
            try:
                from groq import Groq

                self._groq = Groq(
                    api_key=settings.groq_api_key, max_retries=0, timeout=30.0
                )
                logger.info("Groq client ready (fallback)")
            except Exception as e:
                logger.warning("Groq init failed: %s", e)

        if settings.openai_api_key:
            try:
                from openai import OpenAI

                self._openai = OpenAI(
                    api_key=settings.openai_api_key, max_retries=0, timeout=30.0
                )
                logger.info("OpenAI client ready (fallback)")
            except Exception as e:
                logger.warning("OpenAI init failed: %s", e)

        if not any([self._gemini, self._groq, self._openai]):
            raise RuntimeError(
                "No model providers configured. Set GEMINI_API_KEY (recommended)."
            )

    def _on_cooldown(self, provider: str) -> bool:
        return time.time() < _provider_cooldown_until.get(provider, 0)

    def _mark_cooldown(self, provider: str) -> None:
        sec = float(self.settings.provider_cooldown_sec)
        _provider_cooldown_until[provider] = time.time() + sec
        logger.warning("Provider %s cooldown %.0fs", provider, sec)

    def _chain(self) -> list[tuple[str, str]]:
        """(model, provider) priority list."""
        chain: list[tuple[str, str]] = []
        # Gemini first
        if self._gemini and not self._on_cooldown("gemini"):
            chain.append((self.settings.gemini_model, "gemini"))
        # Groq models
        if self._groq and not self._on_cooldown("groq"):
            primary = self.settings.primary_model
            if not primary.startswith("gemini") and not primary.startswith("gpt-"):
                chain.append((primary, "groq"))
            for m in self.settings.fallback_models:
                if m.startswith("gpt-") or m.startswith("gemini"):
                    continue
                if m != primary:
                    chain.append((m, "groq"))
        # OpenAI
        if self._openai and not self._on_cooldown("openai"):
            for m in self.settings.fallback_models:
                if m.startswith("gpt-"):
                    chain.append((m, "openai"))
            if not any(p == "openai" for _, p in chain):
                chain.append(("gpt-4o-mini", "openai"))

        # last resort: ignore cooldown
        if not chain:
            if self._gemini:
                chain.append((self.settings.gemini_model, "gemini"))
            if self._groq:
                chain.append((self.settings.primary_model, "groq"))
            if self._openai:
                chain.append(("gpt-4o-mini", "openai"))
        return chain

    def _chat_gemini(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        use_tools: bool,
        model: str,
    ) -> ChatResult | SyntheticToolCall:
        from google.genai import types

        system, contents = _messages_to_gemini_contents(messages)
        config_kwargs: dict[str, Any] = {
            "temperature": 0.5,
            "max_output_tokens": self.settings.max_tokens,
        }
        if system:
            config_kwargs["system_instruction"] = system

        if use_tools and tools:
            decls = _openai_tools_to_gemini_declaration(tools)
            if decls:
                config_kwargs["tools"] = [
                    types.Tool(function_declarations=decls)
                ]

        try:
            config = types.GenerateContentConfig(**config_kwargs)
        except Exception:
            # Older SDK shape — drop tools if config rejects
            config_kwargs.pop("tools", None)
            config = types.GenerateContentConfig(**config_kwargs)

        response = self._gemini.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        # Function calls from Gemini
        try:
            cand = response.candidates[0]
            parts = cand.content.parts or []
            for part in parts:
                fc = getattr(part, "function_call", None)
                if fc and getattr(fc, "name", None):
                    args = dict(fc.args) if getattr(fc, "args", None) else {}
                    return SyntheticToolCall(name=fc.name, arguments=args)
        except Exception:
            pass

        text = ""
        try:
            text = (response.text or "").strip()
        except Exception:
            text = ""

        recovered = _parse_xml_tool_call(text)
        if recovered:
            name, args = recovered
            return SyntheticToolCall(name=name, arguments=args)

        return ChatResult(
            content=text,
            tool_calls=[],
            model=model,
            provider="gemini",
            raw=response,
        )

    def _chat_openai_compatible(
        self,
        *,
        provider: str,
        model: str,
        messages: list[dict],
        tools: Optional[list],
        use_tools: bool,
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
            return self._groq.chat.completions.create(**kwargs)
        if provider == "openai":
            return self._openai.chat.completions.create(**kwargs)
        raise RuntimeError(provider)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        use_tools: bool = True,
    ) -> ChatResult | SyntheticToolCall:
        last_error: Exception | None = None
        chain = self._chain()
        if not chain:
            raise RuntimeError("No model providers available")

        for model, provider in chain:
            try:
                if provider == "gemini":
                    return self._chat_gemini(
                        messages, tools, use_tools and bool(tools), model
                    )

                resp = self._chat_openai_compatible(
                    provider=provider,
                    model=model,
                    messages=messages,
                    tools=tools,
                    use_tools=use_tools and bool(tools),
                )
                return _normalize_openai_style(
                    resp.choices[0].message, model, provider
                )
            except Exception as e:
                if _is_rate_limit(e):
                    logger.warning("429/quota on %s/%s — failover", provider, model)
                    self._mark_cooldown(provider)
                    last_error = e
                    continue

                if use_tools and _is_tool_use_failed(e):
                    recovered = _parse_xml_tool_call(str(e))
                    if recovered:
                        return SyntheticToolCall(
                            name=recovered[0], arguments=recovered[1]
                        )
                    try:
                        if provider == "gemini":
                            return self._chat_gemini(
                                messages, None, False, model
                            )
                        resp = self._chat_openai_compatible(
                            provider=provider,
                            model=model,
                            messages=messages,
                            tools=None,
                            use_tools=False,
                        )
                        return _normalize_openai_style(
                            resp.choices[0].message, model, provider
                        )
                    except Exception as e2:
                        last_error = e2
                        if _is_rate_limit(e2):
                            self._mark_cooldown(provider)
                        continue

                logger.warning("Error on %s/%s: %s", provider, model, e)
                last_error = e
                continue

        if last_error:
            raise last_error
        raise RuntimeError("All model providers failed")
