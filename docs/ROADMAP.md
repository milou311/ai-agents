# AAOS Roadmap

Aligned with `docs/AAOS_ARCHITECTURE_v1.md`.

## Phase 0 — Constitution & Skeleton ✅

- [x] Architecture Spec, ADR, coding rules, skeleton

## Phase 1 — Modular Runtime ✅

- [x] Models, Memory, Tools, AgentLoop, Telegram interface

## Phase 2 — Planning & Knowledge

- [x] Heuristic Planner (`aaos.planner`)
- [x] Knowledge store TXT/MD chunk search (`aaos.knowledge`)
- [x] Tools: `knowledge_search`, `knowledge_ingest`
- [x] Planner hints injected into AgentLoop
- [x] Executor module for plan steps
- [x] HTTP API (`aaos.interfaces.http`) — `/v1/chat`, knowledge endpoints
- [x] CLI `scripts/ingest_knowledge.py`
- [ ] Embeddings / semantic vector search
- [ ] PDF/DOCX ingest
- [ ] Auth on HTTP API

## Phase 3 — Multi-Agent & Skills

- [ ] Skill graphs
- [ ] Supervisor + specialist agents
- [ ] Plugin loader

## Phase 4 — Production Hardening

- [ ] Permissions & audit log
- [ ] Metrics / tracing
- [ ] Multi-tenant upgrades

## Phase 5+ — Scale

- Enterprise connectors, self-host, evaluation harness
