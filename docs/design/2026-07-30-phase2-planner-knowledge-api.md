# Design Note: Phase 2 — Planner, Knowledge, HTTP API

**Date:** 2026-07-30  
**Status:** In progress

## Goal

1. **Planner** — structured multi-step plans (no side effects)
2. **Knowledge** — ingest TXT/MD, keyword/chunk retrieval (embeddings later)
3. **HTTP API** — thin FastAPI/Starlette-style interface over AgentLoop

## Integration

- AgentLoop may call Planner for complex goals (heuristic or always-on flag)
- Knowledge exposed as tool `knowledge_search` + ingest CLI/API
- HTTP `/v1/chat` accepts same semantic as Telegram text path

## Non-goals this slice

- Full vector DB / embeddings production
- Multi-agent supervisor
