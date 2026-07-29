"""Simple append-only audit log (file-backed)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aaos.config import get_settings


def audit(event: str, **fields: Any) -> None:
    settings = get_settings()
    path = Path(settings.data_dir) / "audit.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
