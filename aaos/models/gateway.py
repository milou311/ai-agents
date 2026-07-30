"""
Unified Model Gateway — multi-provider chat with FAST failover on 429.

On rate limit: skip provider immediately (no 14s client retry loops).
Order: primary → other models on same provider → other providers.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional

from aaos.config import get_settings
from aaos.models.types import ChatResult, SyntheticToolCall, ToolCall
from aaos.monitoring import get_metrics

logger = logging.getLogger(__name__)

# In-process cooldown: after 429, skip this provider for N seconds
_provider_cooldown_until: dict[str, float] = {}


def _is_rate_limit(e: Exception) -> bool:
    if "RateLimit" in type(e).__name__:
        return True
    if getattr(e, "status_code", None) == 429:
        return True
    text = str(e).lower()
    return "rate limit" in text or "too many requests" in text or "429" in text or "resource_exhausted" in text


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
    class ModelGateway:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self._gemini = None

        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                from google import genai
                self._gemini = genai.Client(api_key=gemini_key)
            except Exception as e:
                logger.warning("Gemini init failed: %s", e)

        if not self._gemini:
            raise RuntimeError("No model providers configured")
            
