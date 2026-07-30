"""
Identity Manager — single source of Self-Model.

Phase 5: static identity + live capability inventory (tools, skills, modules).
Phase 6: operational state snapshot (metrics, counts).
Phase 7: reflection from episodic/performance logs (future).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from aaos import __version__ as aaos_version
from aaos.identity.schema import Identity


def _load_identity_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    # Minimal YAML-ish or JSON. Prefer JSON for zero deps.
    text = text.strip()
    if not text:
        return {}
    if path.suffix.lower() in {".json"} or text.startswith("{"):
        return json.loads(text)
    # Very small YAML subset: key: value and lists with "- item"
    data: dict[str, Any] = {}
    current_list: str | None = None
    for line in text.splitlines():
        raw = line.rstrip()
        if not raw or raw.lstrip().startswith("#"):
            continue
        if raw.lstrip().startswith("- ") and current_list:
            data.setdefault(current_list, []).append(raw.lstrip()[2:].strip())
            continue
        if ":" in raw and not raw.strip().startswith("-"):
            key, _, val = raw.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                current_list = key
                data[key] = []
            else:
                current_list = None
                data[key] = val.strip('"\'')
    return data


class IdentityManager:
    def __init__(self, config_path: Optional[Path] = None):
        root = Path(__file__).resolve().parents[2]
        self.config_path = config_path or Path(
            os.getenv("AAOS_IDENTITY_FILE", str(root / "config" / "identity.json"))
        )
        self.identity = self._build_identity()

    def _build_identity(self) -> Identity:
        raw = _load_identity_file(self.config_path)
        base = Identity()
        # Env overrides for quick rename without file edit
        name = os.getenv("AAOS_AGENT_NAME") or raw.get("name") or base.name
        name_en = os.getenv("AAOS_AGENT_NAME_EN") or raw.get("name_en") or base.name_en
        version = (
            os.getenv("AAOS_AGENT_VERSION")
            or raw.get("version")
            or aaos_version
            or base.version
        )
        role = raw.get("role") or base.role

        def _list(key: str, default: list[str]) -> list[str]:
            v = raw.get(key)
            if isinstance(v, list) and v:
                return [str(x) for x in v]
            return list(default)

        return Identity(
            name=str(name),
            name_en=str(name_en),
            version=str(version),
            role=str(role),
            goals=_list("goals", base.goals),
            limits=_list("limits", base.limits),
            strengths=_list("strengths", base.strengths),
            weaknesses=_list("weaknesses", base.weaknesses),
        )

    def reload(self) -> Identity:
        self.identity = self._build_identity()
        return self.identity

    # --- Live inventory (Phase 5) ---

    def list_tools(self) -> list[str]:
        try:
            from aaos.tools import build_default_registry

            reg = build_default_registry()
            return sorted(
                s["function"]["name"] for s in reg.list_specs() if "function" in s
            )
        except Exception:
            return []

    def list_skills(self) -> list[str]:
        try:
            from aaos.skills import SKILLS

            return sorted(SKILLS.keys())
        except Exception:
            return []

    def list_interfaces(self) -> list[str]:
        return ["telegram", "http", "cli"]

    def list_modules(self) -> list[str]:
        return [
            "core",
            "models",
            "memory",
            "planner",
            "executor",
            "tools",
            "knowledge",
            "skills",
            "plugins",
            "identity",
            "security",
            "monitoring",
            "scheduler",
            "interfaces",
        ]

    # --- Phase 6 operational snapshot ---

    def runtime_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {
            "tools_count": len(self.list_tools()),
            "skills_count": len(self.list_skills()),
            "interfaces": self.list_interfaces(),
            "modules": self.list_modules(),
        }
        try:
            from aaos.monitoring import get_metrics

            state["metrics"] = get_metrics().snapshot()
        except Exception:
            state["metrics"] = {}
        try:
            from aaos.plugins import PluginLoader

            plugins = PluginLoader().discover()
            state["plugins_discovered"] = len(plugins)
        except Exception:
            state["plugins_discovered"] = 0
        return state

    # --- Public Self-Model ---

    def self_model(self, include_runtime: bool = True) -> dict[str, Any]:
        model = self.identity.to_dict()
        model["capabilities"] = {
            "tools": self.list_tools(),
            "skills": self.list_skills(),
            "interfaces": self.list_interfaces(),
        }
        if include_runtime:
            model["runtime"] = self.runtime_state()
        return model

    def system_prompt_block(self, include_runtime: bool = False) -> str:
        """Compact block injected into AgentLoop system context."""
        ident = self.identity
        tools = ", ".join(self.list_tools()[:20])
        skills = ", ".join(self.list_skills()) or "(none)"
        lines = [
            f"هويتك: اسمك «{ident.name}» ({ident.name_en})، الإصدار {ident.version}.",
            f"دورك: {ident.role}",
            f"أهدافك: {'; '.join(ident.goals)}",
            f"حدودك: {'; '.join(ident.limits)}",
            f"أدواتك المتاحة: {tools}",
            f"مهاراتك المسجّلة: {skills}",
            "إذا سُئلت من أنت؟ عرّف بنفسك باختصار دون ادعاء وعي أو مشاعر بشرية.",
        ]
        if include_runtime:
            rt = self.runtime_state()
            lines.append(
                f"حالة تشغيلية مختصرة: tools={rt.get('tools_count')} "
                f"skills={rt.get('skills_count')} plugins={rt.get('plugins_discovered')}"
            )
        return "\n".join(lines)

    def introduce(self, lang: str = "ar") -> str:
        ident = self.identity
        if lang.startswith("en"):
            return (
                f"I am {ident.name_en} (v{ident.version}), {ident.role}. "
                f"How can I help you today?"
            )
        return (
            f"أنا {ident.name} (الإصدار {ident.version}). "
            f"{ident.role}. تفضّل، كيف أستطيع خدمتك؟"
        )


_default: IdentityManager | None = None


def get_identity_manager() -> IdentityManager:
    global _default
    if _default is None:
        _default = IdentityManager()
    return _default
