# Design Note: Phase 1 — Tool Registry + Agent Loop

**Date:** 2026-07-29  
**Status:** Approved  
**Related:** Phase 1 Models/Memory

## Goal

- Central `ToolRegistry` under `aaos.tools`
- `AgentLoop` uses `ModelGateway` + `MemoryStore` + registry (no direct Groq SDK in loop)
- Legacy `agents.agent_core.AgentCore` becomes a thin adapter so Telegram keeps working

## Non-goals

- Full Planner module
- Plugin loader
- Rewriting telegram_bot handlers

## Failure modes

Same as ModelGateway + structured tool errors as strings returned to the model.
