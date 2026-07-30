"""HTTP API Interface."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from aaos.config import get_settings
from aaos.core.agent_loop import AgentLoop
from aaos.core.supervisor import Supervisor
from aaos.identity import get_identity_manager
from aaos.identity.state import get_operational_state
from aaos.knowledge import get_knowledge_store
from aaos.memory import get_default_store
from aaos.monitoring import get_metrics

logger = logging.getLogger(__name__)

app = FastAPI(title="AAOS HTTP API", version="0.6.0")
_settings = get_settings()
_loop = AgentLoop()
_supervisor = Supervisor(_loop)
_store = get_default_store()
_knowledge = get_knowledge_store()
_identity = get_identity_manager()


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


async def require_auth(authorization: Optional[str] = Header(None)):
    token = _settings.api_bearer_token
    if not token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    if authorization.removeprefix("Bearer ").strip() != token:
        raise HTTPException(403, "Invalid token")


@app.on_event("startup")
async def _startup():
    await _store.init()
    await _knowledge.init()
    logger.info("AAOS HTTP API ready")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "system": "aaos",
        "metrics": get_metrics().snapshot(),
        "operational": get_operational_state().snapshot(),
    }


@app.get("/v1/identity")
async def identity():
    return _identity.self_model(include_runtime=True)


@app.get("/v1/state")
async def operational_state():
    return get_operational_state().snapshot()


@app.post("/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_auth)])
async def chat(body: ChatBody):
    if not body.message.strip():
        raise HTTPException(400, "message required")
    request_id = str(uuid.uuid4())
    chat_id = body.chat_id or body.user_id
    metrics = get_metrics()
    metrics.inc("http.chat.requests")
    try:
        if _settings.use_supervisor:
            reply = await _supervisor.run(body.user_id, chat_id, body.message)
        else:
            reply = await _loop.run(body.user_id, chat_id, body.message)
        metrics.inc("http.chat.ok")
    except Exception as e:
        metrics.inc("http.chat.errors")
        logger.exception("chat failed")
        raise HTTPException(500, str(e))
    return ChatResponse(request_id=request_id, reply=reply)


@app.post("/v1/knowledge/ingest", dependencies=[Depends(require_auth)])
async def knowledge_ingest(body: IngestBody):
    info = await _knowledge.ingest_text(body.source, body.text, title=body.title)
    get_metrics().inc("knowledge.ingest")
    return info


@app.get("/v1/knowledge/search", dependencies=[Depends(require_auth)])
async def knowledge_search(q: str, limit: int = 5):
    hits = await _knowledge.search(q, limit=limit)
    return {"query": q, "hits": hits}
