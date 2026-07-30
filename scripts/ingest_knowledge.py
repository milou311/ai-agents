#!/usr/bin/env python3
"""CLI: ingest a file (txt/md/pdf/docx) into keyword + semantic knowledge."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aaos.knowledge import get_knowledge_store


async def main():
    p = argparse.ArgumentParser(description="Ingest file into AAOS knowledge (semantic)")
    p.add_argument("path", help="Path to .txt .md .pdf .docx …")
    args = p.parse_args()
    ks = get_knowledge_store()
    info = await ks.ingest_file(args.path)
    print(info)


if __name__ == "__main__":
    asyncio.run(main())
