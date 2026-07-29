# ADR 0001 — Adopt AAOS Modular Architecture

## Status

Accepted

## Context

The project began as a practical Telegram assistant (`agents/` package) with tools, memory, and model failover. Feature growth risked a monolith that is hard to test, replace, or scale into a company-grade platform.

## Decision

Adopt the **AI Agent Operating System (AAOS)** architecture defined in `docs/AAOS_ARCHITECTURE_v1.md` as the normative design.

- New code lands under `aaos/`
- Legacy `agents/` remains until migrated behind Interfaces
- Features are Modules or Plugins, not patches to god-files

## Consequences

**Positive:** Clear boundaries, replaceable providers, long-term extensibility.  
**Negative:** Short-term dual structure (legacy + aaos) during migration.  
**Mitigation:** Adapter layer; migrate one module per phase.
