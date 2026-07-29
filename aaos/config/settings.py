"""Central configuration — no magic numbers in business modules."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    data_dir: str = "./data"
    primary_model: str = "llama-3.3-70b-versatile"
    fallback_models: tuple[str, ...] = ("llama-3.1-8b-instant", "gpt-4o-mini")
    history_limit: int = 8
    max_tool_rounds: int = 5
    max_tokens: int = 1024
    api_bearer_token: str = ""  # if set, HTTP API requires Authorization: Bearer ...
    use_supervisor: bool = False

    @staticmethod
    def from_env() -> "Settings":
        fallbacks = os.getenv(
            "AAOS_MODEL_FALLBACKS", "llama-3.1-8b-instant,gpt-4o-mini"
        )
        return Settings(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            data_dir=os.getenv("AAOS_DATA_DIR", "./data"),
            primary_model=os.getenv(
                "AAOS_MODEL_PRIMARY", "llama-3.3-70b-versatile"
            ),
            fallback_models=tuple(
                m.strip() for m in fallbacks.split(",") if m.strip()
            ),
            history_limit=int(os.getenv("AAOS_HISTORY_LIMIT", "8")),
            max_tool_rounds=int(os.getenv("AAOS_MAX_TOOL_ROUNDS", "5")),
            max_tokens=int(os.getenv("AAOS_MAX_TOKENS", "1024")),
            api_bearer_token=os.getenv("AAOS_API_TOKEN", ""),
            use_supervisor=os.getenv("AAOS_USE_SUPERVISOR", "").lower()
            in {"1", "true", "yes"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
