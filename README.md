<div align="center">

# 🤖 مُعين — AI Agent Operating System (AAOS)

**General-purpose AI Agent platform**  
Telegram interface is one adapter — not the product itself.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![Architecture](https://img.shields.io/badge/Architecture-AAOS%20v1.0-purple.svg)](docs/AAOS_ARCHITECTURE_v1.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## 📜 System Constitution

This repository is governed by:

**→ [`docs/AAOS_ARCHITECTURE_v1.md`](docs/AAOS_ARCHITECTURE_v1.md)**

Also read:

- [`docs/CODING_AGENT_RULES.md`](docs/CODING_AGENT_RULES.md) — rules for Copilot / Cursor / any coding agent
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phases 0 → 10
- [`docs/ADR/`](docs/ADR/) — architecture decisions

> **Do not add features by patching god-files.**  
> Add Modules or Plugins under `aaos/` according to the spec.

---

## 🏗️ Dual structure (Phase 0–1 migration)

| Path | Role |
|------|------|
| `aaos/` | **Target OS** — modular packages (Core, Models, Memory, Tools, …) |
| `agents/` | **Legacy runtime** — current production Telegram bot (being wrapped/migrated) |
| `docs/` | Architecture, ADRs, design notes |
| `tests/` | Unit / contract tests |

Production entry points still use the stable legacy path until Phase 1 completes:

```bash
python bot.py                  # Telegram worker (Render)
python -m agents.telegram_bot  # same
```

---

## 🚀 Run (current production)

```bash
git clone https://github.com/milou311/ai-agents.git
cd ai-agents
python -m venv venv && source venv/bin/activate  # or Windows equivalent
pip install -r requirements.txt
cp .env.example .env   # fill TELEGRAM_BOT_TOKEN, GROQ_API_KEY, optional OPENAI_API_KEY
python bot.py
```

### Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | yes | Bot token |
| `GROQ_API_KEY` | yes | Primary LLM |
| `OPENAI_API_KEY` | no | Fallback when Groq is exhausted |
| `AAOS_MODEL_PRIMARY` | no | Override primary model |
| `AAOS_MODEL_FALLBACKS` | no | Comma-separated fallbacks |
| `AAOS_DATA_DIR` | no | Default `./data` |

---

## 📦 AAOS modules (target)

```text
aaos/
  core/         Orchestrator only
  models/       Provider-agnostic LLM layer
  memory/       Working / long-term / semantic / episodic
  planner/      Plans only (no side effects)
  executor/     Executes plans
  tools/        Tool manager + builtins
  knowledge/    RAG (Phase 2)
  skills/       Skill graphs (Phase 3)
  plugins/      Loadable plugins (Phase 3)
  security/     Permissions, secrets, audit
  scheduler/    Reminders & jobs
  monitoring/   Metrics & health
  config/       Central settings
  interfaces/   Telegram, CLI, Web, API
```

---

## ✅ Tests

```bash
pip install pytest
pytest -q
```

---

## 🗺️ Roadmap (short)

| Phase | Focus |
|-------|--------|
| 0 | Constitution + skeleton (now) |
| 1 | Migrate Core / Models / Memory / Tools off legacy |
| 2 | Planner + Knowledge + HTTP API |
| 3 | Multi-agent + Plugins |
| 4+ | Hardening, multi-tenant, enterprise connectors |

---

## 📄 License

MIT

---

<div align="center">
Built toward a long-lived Agent OS — not a one-off bot.<br/>
<a href="https://github.com/milou311">Mohamed Miloud</a>
</div>
