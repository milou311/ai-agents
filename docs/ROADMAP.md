# AAOS Roadmap

## Phase 0 — Constitution ✅
## Phase 1 — Modular Runtime ✅
## Phase 2 — Planning & Knowledge (core done)
## Phase 3 — Skills / Supervisor (scaffold ✅)
## Phase 4 — Hardening (scaffold ✅)

## Phase 5 — Identity / Self-Model

- [x] `aaos.identity.IdentityManager` — name, version, role, goals, limits
- [x] Live inventory of tools & skills
- [x] Inject identity into AgentLoop system prompt
- [x] Tool `whoami` + HTTP `GET /v1/identity`
- [x] Config file `config/identity.json` + env overrides
- [ ] Richer multi-language intros

## Phase 6 — Operational Self-State

- [x] Basic `runtime_state()` (counts, metrics snapshot)
- [ ] Active tasks / projects dashboard
- [ ] Per-skill success rates
- [ ] Last errors summary for the agent

## Phase 7 — Self-Reflection

- [ ] Episodic performance log
- [ ] Planner consumes failure patterns
- [ ] Explicit "I failed at X, adjusting plan" behavior from data — not claims of consciousness

## Later

- Embeddings, PDF ingest, plugin.yaml load, multi-agent parallel
