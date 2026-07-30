# Design: Fast Rate-Limit Failover

## Problems fixed

1. **429 long waits** — Groq SDK `max_retries` caused ~14s sleeps. Set `max_retries=0`.
2. **Slow replies** — on 429 jump to next model/provider immediately; cooldown skips Groq for 45s.
3. **Persona** — compact Ops identity in Arabic; system prompt only from IdentityManager.

## Required for smooth UX

Set `OPENAI_API_KEY` on Render so failover has a real second provider.
