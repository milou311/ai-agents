<div align="center">

# 🤖 مُعين — AI Agent Operating System (AAOS)

**General-purpose AI Agent platform**  
Telegram is one interface — not the whole product.

[![Architecture](https://img.shields.io/badge/Architecture-AAOS%20v1.0-purple.svg)](docs/AAOS_ARCHITECTURE_v1.md)

</div>

## Constitution

- [`docs/AAOS_ARCHITECTURE_v1.md`](docs/AAOS_ARCHITECTURE_v1.md)
- [`docs/CODING_AGENT_RULES.md`](docs/CODING_AGENT_RULES.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Run Telegram bot

```bash
pip install -r requirements.txt
cp .env.example .env   # TELEGRAM_BOT_TOKEN, GROQ_API_KEY, optional OPENAI_API_KEY
python bot.py
```

## Run HTTP API

```bash
uvicorn aaos.interfaces.http.app:app --host 0.0.0.0 --port 8000
# POST /v1/chat  {"message":"مرحبا","user_id":1}
# POST /v1/knowledge/ingest  {"text":"...","source":"manual"}
# GET  /v1/knowledge/search?q=...
```

## Ingest knowledge file

```bash
python scripts/ingest_knowledge.py ./notes.md
```

## Package layout

```text
aaos/
  core/ models/ memory/ planner/ executor/ tools/ knowledge/
  interfaces/telegram  interfaces/http
  config/ security/ scheduler/ monitoring/ plugins/ skills/
agents/          # legacy shims only
docs/ tests/ scripts/
```

## License

MIT

