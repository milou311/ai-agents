# AI Agent Operating System (AAOS)
## Architecture Specification — Version 1.0

**Status:** Canonical  
**Scope:** System constitution for the General-Purpose AI Agent platform  
**Audience:** Human engineers, coding agents (Copilot / Claude / Cursor), future team members  
**Language:** Technical English (normative). Product UX may remain Arabic.

---

## 0. Mandatory Rules for Any Coding Agent

Before writing or modifying code, every agent (human or AI) MUST follow these rules:

1. **Do not bolt features onto existing monolithic files.**  
   First align the change with this architecture. If the target module does not exist, create it under the correct package.

2. **Every feature is a Module or a Plugin.**  
   No business logic in Interfaces (Telegram, CLI, Web). No tool logic in Core. No provider SDKs outside Models.

3. **Modules communicate only through explicit Interfaces / Protocols.**  
   No direct imports of internal implementation details across module boundaries.

4. **Before non-trivial work, write a short Design Note** under `docs/design/` describing:  
   - Goal  
   - Affected modules  
   - Interface changes  
   - Failure modes  
   - Test plan  

5. **Preserve backward compatibility** of public Interfaces unless a major version bump is declared.

6. **The system must degrade gracefully.**  
   If Models, Tools, or Memory fail, Core still returns a controlled response.

7. **Configuration is external.**  
   No hardcoded API keys, model names as magic strings in business logic, or environment-specific paths.

8. **Tests accompany every Module.**  
   Unit tests for pure logic; contract tests for Interfaces.

---

## 1. Vision

AAOS is not a Telegram bot.  
It is a **long-lived Agent Operating System**: a modular runtime that can:

- Accept goals from multiple Interfaces
- Plan multi-step work
- Use tools safely
- Remember across sessions
- Host specialized sub-agents
- Grow via Plugins for years without rewrite

**Product name (current):** مُعين (Mueen)  
**System name:** AAOS  
**Horizon:** Foundation for a company-scale agent platform (v1 → v10)

---

## 2. Design Principles

| # | Principle | Meaning |
|---|-----------|---------|
| P1 | Module independence | Each package is replaceable |
| P2 | Interface isolation | Depend on protocols, not concrete classes |
| P3 | Plugin-first features | New capability = Plugin, not Core edit |
| P4 | Failure isolation | One broken tool must not crash the OS |
| P5 | Provider agnosticism | Swap Groq/OpenAI/Ollama without touching Planner |
| P6 | Explicit over implicit | Plans, tool calls, and memory writes are logged |
| P7 | Least privilege | Tools and secrets are permission-scoped |
| P8 | Observable by default | Metrics and audit trails are first-class |

---

## 3. System Context

```text
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Telegram   │  │    Web      │  │    CLI      │  │  HTTP API   │
│  Interface  │  │  Interface  │  │  Interface  │  │  Interface  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┴────────┬───────┴────────────────┘
                                 ▼
                          ┌─────────────┐
                          │    CORE     │
                          │  Orchestr.  │
                          └──────┬──────┘
               ┌─────────────────┼─────────────────┐
               ▼                 ▼                 ▼
        ┌────────────┐   ┌────────────┐   ┌────────────┐
        │  Planner   │   │  Executor  │   │   Models   │
        └────────────┘   └─────┬──────┘   └────────────┘
                               ▼
                        ┌────────────┐
                        │   Tools    │
                        │  Manager   │
                        └────────────┘
               ▲                 ▲                 ▲
        ┌────────────┐   ┌────────────┐   ┌────────────┐
        │   Memory   │   │ Knowledge  │   │  Plugins   │
        └────────────┘   └────────────┘   └────────────┘
```

---

## 4. Target Repository Layout

```text
aaos/
├── docs/
│   ├── AAOS_ARCHITECTURE_v1.md      # THIS document (canonical)
│   ├── design/                      # Per-feature design notes
│   ├── ROADMAP.md
│   └── ADR/                         # Architecture Decision Records
├── aaos/
│   ├── __init__.py
│   ├── core/                        # Orchestrator only
│   ├── models/                      # LLM providers
│   ├── memory/                      # Working / Long-term / Semantic / Episodic
│   ├── planner/                     # Plan generation (no execution)
│   ├── executor/                    # Plan execution
│   ├── tools/                       # Tool Manager + built-in tools
│   ├── knowledge/                   # Ingestion + retrieval
│   ├── skills/                      # Reusable skill graphs
│   ├── plugins/                     # Loadable plugins
│   ├── security/                    # Secrets, permissions, audit
│   ├── scheduler/                   # Jobs, reminders, cron-like tasks
│   ├── monitoring/                  # Metrics, health, tracing
│   ├── config/                      # Settings, env mapping
│   └── interfaces/                  # Telegram, CLI, Web, API adapters
├── tests/
├── data/                            # Runtime data (gitignored)
├── bot.py                           # Thin entry (Telegram worker)
├── main.py                          # Thin entry (CLI)
├── pyproject.toml / requirements.txt
└── README.md
```

**Migration note (v1.0 → AAOS layout):**  
Current code under `agents/` is the **legacy monolith**. New work MUST land under `aaos/`. Legacy modules are wrapped behind Interfaces until fully migrated (see Roadmap Phase 0–1).

---

## 5. Module Specifications

### 5.1 Core

**Responsibility:** Orchestrate a single request lifecycle.

**Does:**
- Accept a normalized `AgentRequest`
- Load working memory / user context
- Ask Planner for a `Plan` (optional for simple turns)
- Hand steps to Executor
- Aggregate results into `AgentResponse`
- Emit monitoring events

**Does NOT:**
- Call LLM SDKs directly
- Implement tools
- Parse Telegram updates
- Own database schemas

**Primary types:**
```text
AgentRequest  { request_id, user_id, channel, text, attachments[], metadata }
AgentResponse { request_id, text, attachments[], tool_traces[], error? }
```

**Interface:** `Orchestrator.run(request) -> response`

---

### 5.2 Models

**Responsibility:** Unified access to language / vision / speech models.

**Providers (pluggable):** OpenAI, Groq, Gemini, Anthropic, Ollama, local.

**Interface:**
```text
ModelProvider.chat(messages, tools?, **opts) -> ChatResult
ModelProvider.embed(texts) -> vectors          # optional
ModelProvider.transcribe(audio) -> text        # optional
```

**Rules:**
- Core/Planner never import `groq` or `openai` packages
- Failover chain is configured, not hardcoded in business logic
- Token usage is reported to Monitoring

---

### 5.3 Memory

| Subsystem | Lifetime | Contents |
|-----------|----------|----------|
| Working Memory | Session / turn | Recent messages, current plan state |
| Long-Term Memory | Permanent | User profile, projects, tasks, notes |
| Semantic Memory | Permanent | Embeddings / knowledge chunks |
| Episodic Memory | Permanent | Past agent actions & outcomes |

**Interface:**
```text
MemoryStore.append_message(user_id, role, content)
MemoryStore.get_history(user_id, limit)
MemoryStore.set_note / get_note / list_notes
MemoryStore.add_task / list_tasks / update_task
MemoryStore.record_episode(event)
MemoryStore.search_semantic(query, k)   # Phase 2+
```

**Implementation (v1):** SQLite is acceptable.  
**Implementation (v3+):** Postgres + vector store optional.

---

### 5.4 Planner

**Responsibility:** Produce a structured plan. **Never executes side effects.**

**Output:**
```text
Plan {
  goal: str
  steps: [
    { id, action, tool?, args?, depends_on[], success_criteria }
  ]
  risk_level: low|medium|high
}
```

Simple chat turns may use a **single-step passthrough plan** (direct reply).

---

### 5.5 Executor

**Responsibility:** Run plan steps in order (or parallel when independent).

- Resolves tools via Tool Manager
- Captures outputs into step results
- Stops or replans on hard failure (policy-driven)
- Writes episodic events

**Interface:** `Executor.execute(plan, context) -> ExecutionResult`

---

### 5.6 Tools (Tool Manager)

**Responsibility:** Register, authorize, and invoke tools.

**Built-in tool categories (v1):**
- search (web)
- files (read/write/list/delete — sandboxed per user)
- tasks / reminders / notes
- http_api

**Future:** browser, shell (restricted), email, git, docker, calendar…

**Tool contract:**
```text
Tool.spec -> { name, description, parameters_json_schema, permissions[] }
Tool.run(args, ctx) -> ToolResult { ok, data, error? }
```

**Rules:**
- Every tool declares required permissions
- Path traversal and SSRF protections are mandatory for file/http tools
- Tool errors become structured `ToolResult`, never uncaught crashes in Core

---

### 5.7 Knowledge Engine

**Responsibility:** Ingest documents and retrieve relevant chunks.

**Sources:** PDF, DOCX, TXT, Markdown, web pages, GitHub repos.

**Pipeline:** ingest → chunk → embed → store → retrieve.

**Phase:** Scaffold in v1; production retrieval in v2–v3.

---

### 5.8 Skills

**Responsibility:** Named, reusable multi-step procedures (skill graphs) composed of tools + prompts.

Example skills: `research_topic`, `weekly_report`, `code_review_pr`.

Skills are data + light code, not buried in Core.

---

### 5.9 Plugins

**Responsibility:** Hot-loadable feature packs.

**Examples:** Voice, Image, OCR, Translation, Finance, Research, Security, Coding.

**Plugin manifest:**
```text
plugin.yaml
  name, version, entrypoint
  provides: [tools[], skills[], routes[]]
  requires_permissions: []
```

Core discovers plugins at startup; failure to load one plugin must not block others.

---

### 5.10 Multi-Agent (Phase 3+)

Specialized agents coordinated by a supervisor:

```text
CEO / Supervisor
  ├── Planner Agent
  ├── Research Agent
  ├── Coding Agent
  ├── Review Agent
  ├── Testing Agent
  └── Deployment Agent
```

Each agent is still just Core + different skill/tool policy profiles.

---

### 5.11 Scheduler

**Responsibility:** Time-based work: reminders, recurring jobs, overnight batches.

Must work with process restarts (persistent job store).

---

### 5.12 Monitoring

**Tracks:** request latency, token usage per provider, tool error rates, queue depth, health checks.

**Sinks (configurable):** logs, Prometheus-compatible metrics, optional OpenTelemetry.

---

### 5.13 Configuration

Single settings object loaded from env + optional YAML.

```text
AAOS_ENV=production
TELEGRAM_BOT_TOKEN=...
GROQ_API_KEY=...
OPENAI_API_KEY=...
AAOS_MODEL_PRIMARY=llama-3.3-70b-versatile
AAOS_MODEL_FALLBACKS=llama-3.1-8b-instant,gpt-4o-mini
AAOS_DATA_DIR=./data
```

---

### 5.14 Security

- Secrets only via env / secret manager
- Permission scopes on tools (`files:write`, `net:outbound`, …)
- Audit log for tool invocations and memory writes
- User data isolation (per `user_id` tenant boundary)

---

### 5.15 Interfaces

Adapters only: translate external events ↔ `AgentRequest` / `AgentResponse`.

| Interface | Priority |
|-----------|----------|
| Telegram  | v1 (current) |
| CLI       | v1 |
| HTTP API  | v2 |
| Web UI    | v3 |
| Discord / WhatsApp | later |

---

## 6. Request Lifecycle (Normative)

```text
1. Interface receives event
2. Interface builds AgentRequest
3. Security authenticates / authorizes channel user
4. Core loads Memory (working + relevant long-term)
5. Core → Planner (or direct reply policy)
6. Executor runs steps via Tool Manager + Models
7. Core updates Memory + Episodic log
8. Monitoring records metrics
9. Interface delivers AgentResponse
```

**Idempotency:** `request_id` should be unique per inbound event to avoid double execution where possible.

---

## 7. Error & Degradation Policy

| Failure | Behavior |
|---------|----------|
| Model rate limit | Fail over provider/model; else user-visible wait message |
| tool_use_failed | Recover args if possible; else answer without tools |
| Single tool exception | Mark step failed; continue or replan per policy |
| Memory DB down | Working-only mode; warn in logs |
| Plugin load error | Skip plugin; boot continues |

Never expose raw stack traces to end users.

---

## 8. Testing Strategy

- **Unit:** Planner pure functions, tool arg validation, memory repos
- **Contract:** ModelProvider fakes, Tool fakes
- **Integration:** Core + in-memory memory + mock model
- **E2E (optional):** Telegram test bot in staging

CI must run unit + contract tests on every PR.

---

## 9. Versioning

- **AAOS Spec version** (this document): SemVer for architecture breaks
- **Python package version:** independent SemVer
- **ADR required** for any change that breaks module Interfaces

---

## 10. Roadmap (Summary)

| Phase | Version | Focus |
|-------|---------|-------|
| 0 | 1.0 | Spec + package skeleton + wrap legacy |
| 1 | 1.x | Migrate Core / Models / Memory / Tools off `agents/` monolith |
| 2 | 2.x | Knowledge + better Planner + HTTP API |
| 3 | 3.x | Multi-agent + Skills marketplace |
| 4 | 4.x | Hardened Security, multi-tenant, observability |
| 5–10 | 5–10 | Scale, enterprise connectors, self-host suite |

See `docs/ROADMAP.md` for detail.

---

## 11. Definition of Done (for any change)

- [ ] Matches a module boundary in this spec
- [ ] Design note if non-trivial
- [ ] Interface-compatible
- [ ] Tests added/updated
- [ ] Config, not hardcoding
- [ ] Graceful failure behavior documented
- [ ] No secrets committed

---

## 12. Document Control

| Field | Value |
|-------|-------|
| Title | AAOS Architecture Specification |
| Version | 1.0 |
| Status | Canonical |
| Owners | Project maintainers |
| Review cycle | On each major phase |

**This file is the constitution.**  
If code and this document disagree, **fix the document first**, then update code—or file an ADR to change the document.
