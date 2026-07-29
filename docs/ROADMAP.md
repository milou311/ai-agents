# AAOS Roadmap

Aligned with `docs/AAOS_ARCHITECTURE_v1.md`.

## Phase 0 — Constitution & Skeleton (current)

- [x] Publish Architecture Spec v1.0
- [ ] Create `aaos/` package tree with Interfaces (Protocols)
- [ ] Add ADR folder and template
- [ ] Wrap legacy `agents/` behind thin adapters (no big-bang rewrite)
- [ ] Document coding-agent rules in README

## Phase 1 — Modular Runtime

- [ ] `aaos.models` with Groq + OpenAI providers + failover
- [ ] `aaos.memory` (SQLite) extracted from legacy
- [ ] `aaos.tools` registry + migrate existing tools
- [ ] `aaos.core` orchestrator
- [ ] `aaos.interfaces.telegram` adapter using Core only
- [ ] Unit/contract tests for Core and Tools

## Phase 2 — Planning & Knowledge

- [ ] Real Planner (structured plans for complex goals)
- [ ] Knowledge ingest (TXT/MD first, then PDF)
- [ ] Semantic search (embeddings)
- [ ] HTTP API interface

## Phase 3 — Multi-Agent & Skills

- [ ] Skill graphs
- [ ] Supervisor + specialist agent profiles
- [ ] Plugin loader with manifests

## Phase 4 — Production Hardening

- [ ] Permissions & audit log
- [ ] Metrics / tracing
- [ ] Multi-tenant isolation upgrades
- [ ] Backup & migration tooling

## Phase 5+ — Scale

- Enterprise connectors (GitHub, Slack, email, calendars)
- Self-host distribution
- Evaluation harness & quality benchmarks
