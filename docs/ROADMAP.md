# AAOS Roadmap

Aligned with `docs/AAOS_ARCHITECTURE_v1.md`.

## Phase 0 — Constitution & Skeleton

- [x] Publish Architecture Spec v1.0
- [x] Create `aaos/` package tree with Interfaces (Protocols)
- [x] Add ADR folder and template
- [x] Document coding-agent rules in README
- [x] Design-note template

## Phase 1 — Modular Runtime

- [x] `aaos.models` gateway (Groq + OpenAI failover, tool_use_failed recovery)
- [x] `aaos.memory` SQLite store + legacy shim
- [ ] `aaos.tools` registry + migrate existing tools
- [ ] Wire `AgentCore` / Orchestrator to ModelGateway
- [ ] `aaos.interfaces.telegram` adapter using Core only
- [ ] Unit/contract tests expanded for Core and Tools

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
