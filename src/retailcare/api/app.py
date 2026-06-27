"""FastAPI service: chat endpoint with HITL + trace exposure, and a static web UI.

POST /chat       {user_id, message, thread_id?}            -> reply | interrupt
POST /confirm    {thread_id, user_id, decision}            -> reply (resume HITL)
GET  /trace/{session}                                       -> structured trace JSON
GET  /            -> web/index.html (conversation + trace visualizer)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from retailcare.api.auth import current_user
from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation, resume_existing
from retailcare.memory.summary import summarize_trace

_WEB = Path(__file__).resolve().parents[3] / "web"
_SESSIONS: dict[str, Conversation] = {}


def _seed_enabled() -> bool:
    return os.getenv("RETAILCARE_SEED_ON_STARTUP", "true").strip().lower() in {
        "1", "true", "yes", "on",
    }


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    if _seed_enabled():
        seed(reset=True)
    yield


app = FastAPI(title="RetailCare Orchestrator", lifespan=_lifespan)


# user_id is intentionally NOT in the request body — it comes from the authenticated
# bearer token (api/auth.py), so a caller cannot act as another customer (D11).
class ChatIn(BaseModel):
    message: str
    thread_id: str | None = None


class ConfirmIn(BaseModel):
    thread_id: str
    decision: str


def _assert_thread_owner(conv: Conversation, user_id: str) -> None:
    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="thread_id does not belong to user_id")


def _chat_conversation(user_id: str, thread_id: str | None = None) -> Conversation:
    if thread_id and thread_id in _SESSIONS:
        conv = _SESSIONS[thread_id]
        _assert_thread_owner(conv, user_id)
        return conv
    conv = Conversation(user_id=user_id, thread_id=thread_id)
    _SESSIONS[conv.thread_id] = conv
    return conv


def _resume_conversation(user_id: str, thread_id: str) -> Conversation:
    conv = _SESSIONS.get(thread_id)
    if conv is None:
        conv = resume_existing(thread_id, user_id)
        _SESSIONS[thread_id] = conv
        return conv
    _assert_thread_owner(conv, user_id)
    return conv


def _payload(conv: Conversation, res) -> dict:
    return {
        "thread_id": conv.thread_id,
        "session": conv.trace.session_id,
        "reply": res.reply,
        "interrupted": res.interrupted,
        "interrupt": res.interrupt,
        "tools": [e.name for e in conv.trace.events if e.kind == "tool_call"],
        "summary": summarize_trace(conv.trace).to_dict(),
    }


@app.post("/chat")
def chat(inp: ChatIn, user_id: str = Depends(current_user)) -> dict:
    conv = _chat_conversation(user_id, inp.thread_id)
    return _payload(conv, conv.send(inp.message))


@app.post("/confirm")
def confirm(inp: ConfirmIn, user_id: str = Depends(current_user)) -> dict:
    conv = _resume_conversation(user_id, inp.thread_id)
    return _payload(conv, conv.confirm(inp.decision))


@app.get("/trace/{session}")
def get_trace(session: str, user_id: str = Depends(current_user)) -> dict:
    for conv in _SESSIONS.values():
        if conv.trace.session_id == session:
            if conv.user_id != user_id:
                raise HTTPException(status_code=403, detail="trace does not belong to user")
            return conv.trace.to_dict()
    raise HTTPException(status_code=404, detail="session not found")


@app.get("/trace/thread/{thread_id}")
def get_trace_by_thread(thread_id: str, user_id: str = Depends(current_user)) -> dict:
    """Durable trace lookup (survives restart). Ownership enforced from the stored
    record's user_id, not in-memory session state (D12/D11)."""
    from retailcare.trace import store as trace_store
    rec = trace_store.load(thread_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="trace not found")
    if rec.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="trace does not belong to user")
    return rec


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_WEB / "index.html"))


if _WEB.exists():
    app.mount("/static", StaticFiles(directory=str(_WEB)), name="static")
