# Design Note: Identity Manager & Self-Model

**Date:** 2026-07-30  
**Status:** Approved  
**Phases:** 5 (identity), 6 (runtime state), 7 (self-reflection)

## Goal

Give the agent a **Self-Model** (not consciousness):

- Knows name, version, role
- Knows tools and skills it actually has
- Knows declared limits and goals
- (Phase 6) Knows operational state
- (Phase 7) Uses performance history for better plans

## Module

`aaos.identity` — single source of truth.

Core/AgentLoop injects a compact identity block into the system prompt.
Changing name/version/goals happens only in identity config.

## Non-goals

- Claiming sentience or emotions
- Hardcoding identity strings across Telegram/HTTP handlers
