"""Permission scopes for tools."""

from __future__ import annotations

from typing import Iterable

PERM_NET = "net:outbound"
PERM_FILES_READ = "files:read"
PERM_FILES_WRITE = "files:write"
PERM_MEMORY_WRITE = "memory:write"
PERM_KNOWLEDGE_WRITE = "knowledge:write"

DEFAULT_USER_PERMISSIONS = {
    PERM_NET,
    PERM_FILES_READ,
    PERM_FILES_WRITE,
    PERM_MEMORY_WRITE,
    PERM_KNOWLEDGE_WRITE,
}

TOOL_PERMISSIONS: dict[str, set[str]] = {
    "web_search": {PERM_NET},
    "call_api": {PERM_NET},
    "read_file": {PERM_FILES_READ},
    "list_files": {PERM_FILES_READ},
    "write_file": {PERM_FILES_WRITE},
    "delete_file": {PERM_FILES_WRITE},
    "manage_tasks": {PERM_MEMORY_WRITE},
    "manage_reminders": {PERM_MEMORY_WRITE},
    "manage_notes": {PERM_MEMORY_WRITE},
    "knowledge_search": set(),
    "knowledge_ingest": {PERM_KNOWLEDGE_WRITE},
    "whoami": set(),
}


def check_tool_permission(tool_name: str, granted: Iterable[str]) -> bool:
    needed = TOOL_PERMISSIONS.get(tool_name, set())
    if not needed:
        return True
    granted_set = set(granted)
    return needed.issubset(granted_set)
