"""
Unified Model Gateway — Gemini 1.5 Flash Stable Provider
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional

from aaos.config import get_settings
from aaos.models.types import ChatResult, SyntheticToolCall

logger = logging.getLogger(__name__)

_provider_cooldown_until: dict[str, float] = {}


def _is_rate_limit(e: Exception) -> bool:
    if "RateLimit" in type(e).__name__:
        return True
    if getattr(e, "status_code", None) == 429:
        return True
    text = str(e).lower()
    return "rate limit" in text or "too many requests" in text or "429" in text or "resource_exhausted" in text


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


class ModelGateway:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.client = None

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=gemini_key)
                logger.info("Google GenAI Client initialized successfully.")
            except Exception as e:
                logger.warning("Google GenAI init failed: %s", e)

        if not self.client:
            raise RuntimeError("No model providers configured")

    def _on_cooldown(self, provider: str) -> bool:
        until = _provider_cooldown_until.get(provider, 0.0)
        return time.time() < until

    def _mark_cooldown(self, provider: str) -> None:
        sec = float(getattr(self.settings, "provider_cooldown_sec", 60.0))
        _provider_cooldown_until[provider] = time.time() + sec
        logger.warning("Marked provider %s on cooldown for %.0fs", provider, sec)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        use_tools: bool = True,
        system_prompt: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
    ) -> ChatResult:
        if not self.client:
            raise RuntimeError("No model providers configured")

        if self._on_cooldown("gemini"):
            raise RuntimeError("Gemini provider is currently on cooldown.")

        formatted_prompt = ""
        if system_prompt:
            formatted_prompt += f"System: {system_prompt}\n\n"

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_prompt += f"{role.capitalize()}: {content}\n"

        try:
            # استخدام نموذج gemini-1.5-flash المستقر والمدعوم رسمياً
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=formatted_prompt,
            )
            
            text_response = response.text if response and hasattr(response, 'text') else ""

            xml_tool = _parse_xml_tool_call(text_response)
            tool_calls = []
            if xml_tool:
                name, args = xml_tool
                tool_calls.append(SyntheticToolCall(id="call_gemini", name=name, args=args))

            return ChatResult(
                content=text_response,
                tool_calls=tool_calls,
                raw_response=response,
            )

        except Exception as e:
            logger.error("Gemini execution error: %s", e)
            if _is_rate_limit(e):
                self._mark_cooldown("gemini")
            raise e
            
