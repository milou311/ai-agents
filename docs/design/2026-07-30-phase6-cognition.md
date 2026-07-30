# Design: Phase 6 Self-State + Higher Cognition

## Modules

| Module | Path | Role |
|--------|------|------|
| Operational state | `aaos/identity/state.py` | Tasks, errors, skill stats, metrics |
| Reflection | `aaos/cognition/reflection.py` | Critique answer vs goal before delivery |
| Tree of Thoughts | `aaos/cognition/tot.py` | Generate N paths, score, pick best |
| A2A bus | `aaos/cognition/a2a.py` | Agent-to-agent messages without Supervisor hop |

## Integration

- AgentLoop optionally runs Reflection on final text (flag / complex goals).
- ToT used when Planner marks risk medium/high or explicit multi-path.
- A2A is in-process mailbox; specialists publish partial results.

## Non-goals

- Full distributed multi-host agents
- Claiming consciousness
