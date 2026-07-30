# Design Note: Semantic Memory Layer

**Date:** 2026-07-30  
**Status:** Approved

## Placement

Independent under `aaos/knowledge/` — not inside Telegram, Planner, or Executor.

```text
knowledge/
  embeddings/   embedder, vector_store, search, indexer
  loaders/      txt, pdf, docx
  store.py      legacy keyword + orchestration
```

## Behavior

1. Ingest → chunk → embed → vector DB
2. Query → embed query → top-k cosine → optional keyword merge
3. Agent receives only top chunks (cheaper, more accurate)

## Providers

- OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` set
- Local hashing embedder fallback (no external call)

## Not learning

Embeddings = smart retrieval memory, not self-improvement.
