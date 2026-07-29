# Design Note: Phase 1 — Models Gateway + Memory Store

**Date:** 2026-07-29  
**Status:** Approved  
**Related ADR:** 0001

## Goal

Extract LLM access and persistent memory into `aaos.models` and `aaos.memory` without breaking the live Telegram bot.

## Non-goals

- Full Planner/Executor rewrite
- Moving Telegram interface yet
- Vector/semantic memory

## Affected modules

- `aaos/models/` — new gateway + providers
- `aaos/memory/` — SQLite store class
- `agents/memory.py` — thin re-export / compatibility shim
- `agents/agent_core.py` — may optionally use gateway later; **not required this PR**

## Interface changes

```text
ModelGateway.chat(messages, tools=None, use_tools=True) -> ChatResult | SyntheticToolCall
MemoryStore.init() / get_history / add_message / notes / tasks / reminders
```

## Failure modes

- Rate limit → try next model/provider
- tool_use_failed → recover XML or retry without tools
- DB errors → raise to caller; Core maps to user-safe message

## Test plan

- Unit tests for Settings, MemoryStore (temp DB), ModelGateway error helpers
- Production path unchanged: `python bot.py` still uses legacy AgentCore

## Rollout

1. Land aaos modules
2. Shim legacy memory to same DB path
3. Next PR: AgentCore consumes ModelGateway
