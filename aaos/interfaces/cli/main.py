"""CLI Interface — interactive chat with AgentLoop."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aaos.core.agent_loop import AgentLoop
from aaos.memory import get_default_store


async def run_cli(user_id: int = 0):
    store = get_default_store()
    await store.init()
    loop = AgentLoop()
    print("مُعين CLI — اكتب /exit للخروج، /reset للمسح")
    while True:
        try:
            text = input("أنت: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in {"/exit", "exit", "خروج"}:
            break
        if text in {"/reset", "reset"}:
            await store.clear_history(user_id)
            print("تم المسح.")
            continue
        reply = await loop.run(user_id, user_id, text)
        print(f"مُعين: {reply}\n")


def main():
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
