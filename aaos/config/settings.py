"""Central configuration — Gemini only."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = ""
    gemini_api_key: str = ""
    data_dir: str = "./data"
    gemini_model: str = "gemini-2.5-flash"
    history_limit: int = 6
    max_tool_rounds: int = 4
    max_tokens: int = 768
    api_bearer_token: str = ""
    use_supervisor: bool = False
    provider_cooldown_sec: float = 45.0
    enable_reflection: bool = False
    enable_tot: bool = False

    @staticmethod
    def from_env() -> "Settings":
        def _flag(name: str, default: bool) -> bool:
            v = os.getenv(name)
            if v is None:
                return default
            return v.lower() in {"1", "true", "yes", "on"}

        gemini_key = (
            os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        )

        return Settings(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            gemini_api_key=gemini_key,
            data_dir=os.getenv("AAOS_DATA_DIR", "./data"),
            gemini_model=os.getenv("AAOS_GEMINI_MODEL", "gemini-2.5-flash"),
            history_limit=int(os.getenv("AAOS_HISTORY_LIMIT", "6")),
            max_tool_rounds=int(os.getenv("AAOS_MAX_TOOL_ROUNDS", "4")),
            max_tokens=int(os.getenv("AAOS_MAX_TOKENS", "768")),
            api_bearer_token=os.getenv("AAOS_API_TOKEN", ""),
            use_supervisor=os.getenv("AAOS_USE_SUPERVISOR", "").lower()
            in {"1", "true", "yes"},
            provider_cooldown_sec=float(os.getenv("AAOS_PROVIDER_COOLDOWN_SEC", "45")),
            enable_reflection=_flag("AAOS_ENABLE_REFLECTION", False),
            enable_tot=_flag("AAOS_ENABLE_TOT", False),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
