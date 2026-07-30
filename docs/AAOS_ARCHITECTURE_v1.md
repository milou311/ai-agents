# AI Agent Operating System (AAOS)
## Architecture Specification — Version 1.1

**Status:** Canonical  
**Change in 1.1:** Added **Identity / Self-Model** module (Phase 5–7).

See full Phase 0–1 content in git history; this amendment defines Identity.

---

## Amendment: Identity Manager (Self-Model)

### What it is

A **Self-Model / Self-Representation** — not consciousness.

The agent can know:

| Layer | Content | Phase |
|-------|---------|-------|
| Identity | Name, version, role, goals, limits, strengths/weaknesses | 5 |
| Capabilities | Actual tools, skills, interfaces from the running system | 5 |
| Runtime state | Counts, metrics, plugins discovered | 6 |
| Reflection | Performance history → better plans | 7 |

### Package

```text
aaos/identity/
  schema.py      # Identity dataclass
  manager.py     # IdentityManager — single source of truth
config/identity.json
```

### Rules

1. Identity strings are **not** duplicated across Telegram/HTTP prompts.
2. AgentLoop injects `IdentityManager.system_prompt_block()`.
3. Rename the agent by editing `config/identity.json` or `AAOS_AGENT_NAME`.
4. Never claim human emotions or sentience in identity text.

### Interfaces

- Tool: `whoami`
- HTTP: `GET /v1/identity`
- Programmatic: `get_identity_manager().self_model()`

### System tree (updated)

```text
AAOS
├── Core
├── Models
├── Memory
├── Planner
├── Executor
├── Tools
├── Knowledge
├── Skills
├── Plugins
├── Identity      ← NEW
├── Security
├── Scheduler
├── Monitoring
├── Configuration
└── Interfaces
```

Full original constitution v1.0 remains normative for all other modules.
