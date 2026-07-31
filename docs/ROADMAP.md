# AAOS Roadmap (Gemini-only)

## Done
- Phase 0–1 Runtime
- Phase 2 Knowledge / semantic layer
- Phase 5 Identity (Ops)
- Phase 6 Operational Self-State
- Cognition foundations: Reflection, Tree-of-Thoughts, A2A bus
- Provider: **Gemini only** (Groq/OpenAI removed)

## Cognition usage (flags)
```bash
AAOS_ENABLE_REFLECTION=true   # critique before delivery
AAOS_ENABLE_TOT=true          # multi-path planning for complex goals
AAOS_USE_SUPERVISOR=true      # specialist routing + A2A assignment
AAOS_GEMINI_MODEL=gemini-2.5-flash
```

Default: both reflection and ToT are **off** to protect free-tier quota.
Enable after basic chat is stable.

## Next (Phase 7)
- Persist reflection outcomes into episodic memory
- Planner consumes failure patterns long-term
- Skill learning from successful tool chains
