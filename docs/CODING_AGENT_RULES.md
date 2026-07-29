# Rules for Coding Agents (Copilot, Cursor, Claude, …)

You are working on **AAOS**, not a throwaway bot.

## Before any code

1. Read `docs/AAOS_ARCHITECTURE_v1.md`.
2. Identify the **single module** your change belongs to.
3. If the change is non-trivial, add `docs/design/<feature>.md` from the template.

## While coding

- Put new logic under `aaos/<module>/`.
- Do **not** add features directly into `agents/telegram_bot.py` or `agents/agent_core.py` unless fixing a critical production bug; prefer extracting into `aaos/`.
- Depend on Protocols/Interfaces, not concrete SDKs, from Core/Planner.
- Handle failures; return structured errors.
- No secrets in source.

## After coding

- Update tests under `tests/`.
- Update ROADMAP checkboxes if a phase item was completed.
- Do not expand scope beyond the design note.
