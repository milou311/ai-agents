# Design: Gemini-only + Cognition wiring

## Provider
Only `ModelGateway` → Google GenAI.
On failure: try alternate Gemini model ids, then retry without tools.

## Cognition
`CognitionOrchestrator` centralizes:
- ToT context injection (when enabled + medium/high risk)
- Reflection before delivery (when enabled + long draft)
- A2A publish of plan/tool/result events

Supervisor still uses A2A for assignment/result without micro-managing every tool step.
