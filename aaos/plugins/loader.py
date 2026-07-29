"""
Plugin loader scaffold.

Looks for packages under aaos/plugins/contrib/ with plugin.yaml later.
Currently registers nothing dynamically — safe no-op discovery API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    name: str
    version: str = "0.0.0"
    path: str = ""
    loaded: bool = False
    error: str | None = None


class PluginLoader:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).resolve().parent / "contrib"
        self.plugins: list[PluginInfo] = []

    def discover(self) -> list[PluginInfo]:
        self.plugins = []
        if not self.root.exists():
            return self.plugins
        for child in self.root.iterdir():
            if child.is_dir() and not child.name.startswith("_"):
                info = PluginInfo(name=child.name, path=str(child))
                # Future: parse plugin.yaml and import entrypoint
                info.loaded = False
                info.error = "manifest loading not implemented yet"
                self.plugins.append(info)
                logger.info("Discovered plugin stub: %s", child.name)
        return self.plugins
