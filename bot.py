"""
Production entry point.

Uses AAOS Telegram interface when available; falls back to legacy module path.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    try:
        from aaos.interfaces.telegram import main
    except Exception:
        from agents.telegram_bot import main
    main()
