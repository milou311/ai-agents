"""
HTTP API Interface — FastAPI adapter over AgentLoop.

Run:
  uvicorn aaos.interfaces.http.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from aaos.core.agent_loop import AgentLoop
from aaos.knowledge import get_knowledge_store
from aaos.memory import get_default_store

logger = logging.getLogger(__name__)

app = FastAPI(title="AAOS HTTP API", version="0.2.0")
_loop = AgentLoop()
_store = get_default_store()
_knowledge = get_knowledge_store()


class ChatBody(BaseModel):
    message: str
    user_id: int = 1
    chat_id: Optional[int] = None


class ChatResponse(BaseModel):
    request_id: str
    reply: str


class IngestBody(BaseModel):
    text: str
    source: str = "api"
    title: Optional[str] = None


@app.on_event("startup")
async def _startup():
    await _store.init()
    await _knowledge.init()
    logger.info("AAOS HTTP API ready")


@app.get("/health")
async def health():
    return {"status": "ok", "system": "aaos"}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(body: ChatBody):
    if not body.message.strip():
        raise HTTPException(400, "message required")
    request_id = str(uuid.uuid4())
    chat_id = body.chat_id or body.user_id
    try:
        reply = await _loop.run(body.user_id, chat_id, body.message)
    except Exception as e:
        logger.exception("chat failed")
        raise HTTPException(500, str(e))
    return ChatResponse(request_id=request_id, reply=reply)


@app.post("/v1/knowledge/ingest")
async def knowledge_ingest(body: IngestBody):
    info = await _knowledge.ingest_text(body.source, body.text, title=body.title)
    return info


@app.get("/v1/knowledge/search")
async def knowledge_search(q: str, limit: int = 5):
    hits = await _knowledge.search(q, limit=limit)
    return {"query": q, "hits": hits}
