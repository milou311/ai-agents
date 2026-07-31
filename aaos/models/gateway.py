"""
Model Gateway — Gemini ONLY.

Requires: GEMINI_API_KEY or GOOGLE_API_KEY
Model default: gemini-2.5-flash (override with AAOS_GEMINI_MODEL)
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Optional

from aaos.config import get_settings
from aaos.models.types import ChatResult, SyntheticToolCall

logger = logging.getLogger(__name__)

_cooldown_until: float = 0.0


def _is_rate_limit(e: Exception) -> bool:
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
    ) or getattr(e, "status_code", None) == 429


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


def _messages_to_gemini(messages: list[dict]) -> tuple[str | None, list[dict]]:
    system_parts: list[str] = []
    contents: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role == "system":
            system_parts.append(str(content))
        elif role == "tool":
            contents.append(
                {"role": "user", "parts": [{"text": f"[tool result]\n{content}"}]}
            )
        elif role == "assistant":
            extra = ""
            tcs = m.get("tool_calls") or []
            if tcs:
                names = [
                    (tc.get("function") or {}).get("name", "tool") for tc in tcs
                ]
                extra = f"\n[calling tools: {', '.join(names)}]"
            contents.append(
                {"role": "model", "parts": [{"text": str(content) + extra}]}
            )
        else:
            contents.append({"role": "user", "parts": [{"text": str(content)}]})
    system = "\n".join(system_parts) if system_parts else None
    if not contents:
        contents = [{"role": "user", "parts": [{"text": "."}]}]
    return system, contents


def _tools_to_gemini_decls(tools: list[dict]) -> list[dict]:
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
        self._client = None

        key = settings.gemini_api_key
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) مطلوب. "
                "احصل عليه من https://aistudio.google.com/apikey"
            )
        try:
            from google import genai

            self._client = genai.Client(api_key=key)
            logger.info("Gemini-only gateway ready (model=%s)", settings.gemini_model)
        except Exception as e:
            raise RuntimeError(f"فشل تهيئة Gemini: {e}") from e

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        use_tools: bool = True,
    ) -> ChatResult | SyntheticToolCall:
        global _cooldown_until
        if time.time() < _cooldown_until:
            raise RuntimeError(
                "Gemini في فترة انتظار بعد نفاد الحصة. حاول بعد قليل."
            )

        from google.genai import types

        system, contents = _messages_to_gemini(messages)
        model = self.settings.gemini_model

        config_kwargs: dict[str, Any] = {
            "temperature": 0.5,
            "max_output_tokens": self.settings.max_tokens,
        }
        if system:
            config_kwargs["system_instruction"] = system

        if use_tools and tools:
            decls = _tools_to_gemini_decls(tools)
            if decls:
                try:
                    config_kwargs["tools"] = [
                        types.Tool(function_declarations=decls)
                    ]
                except Exception:
                    pass

        try:
            config = types.GenerateContentConfig(**config_kwargs)
        except Exception:
            config_kwargs.pop("tools", None)
            config = types.GenerateContentConfig(**config_kwargs)

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            if _is_rate_limit(e):
                sec = float(self.settings.provider_cooldown_sec)
                _cooldown_until = time.time() + sec
                logger.warning("Gemini rate/quota limit — cooldown %.0fs", sec)
            raise

        # Native function calls
        try:
            for part in response.candidates[0].content.parts or []:
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
            return SyntheticToolCall(name=recovered[0], arguments=recovered[1])

        return ChatResult(
            content=text,
            tool_calls=[],
            model=model,
            provider="gemini",
            raw=response,
        )
