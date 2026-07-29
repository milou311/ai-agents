"""
Root entry point for deployment (Render, Railway, local, etc.).

Usage:
    python bot.py
"""

import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH so `import agents` always works
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.telegram_bot import main

if __name__ == "__main__":
    main()
