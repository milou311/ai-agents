#!/usr/bin/env python3
"""CLI: ingest a TXT/MD file into the knowledge base."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aaos.knowledge import get_knowledge_store


async def main():
    p = argparse.ArgumentParser(description="Ingest file into AAOS knowledge")
    p.add_argument("path", help="Path to .txt or .md file")
    args = p.parse_args()
    ks = get_knowledge_store()
    info = await ks.ingest_file(args.path)
    print(info)


if __name__ == "__main__":
    asyncio.run(main())
