"""FastAPI service: chat endpoint with HITL + trace exposure, and a static web UI.

POST /chat       {user_id, message, thread_id?}            -> reply | interrupt
POST /confirm    {thread_id, user_id, decision}            -> reply (resume HITL)
GET  /trace/{session}                                       -> structured trace JSON
GET  /            -> web/index.html (conversation + trace visualizer)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation, resume_existing
from retailcare.memory.summary import summarize_trace

app = FastAPI(title="RetailCare Orchestrator")
_WEB = Path(__file__).resolve().parents[3] / "web"
_SESSIONS: dict[str, Conversation] = {}


@app.on_event("startup")
def _startup() -> None:
    seed(reset=True)


class ChatIn(BaseModel):
    user_id: str
    message: str
    thread_id: str | None = None


class ConfirmIn(BaseModel):
    thread_id: str
    user_id: str
    decision: str


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
def chat(inp: ChatIn) -> dict:
    conv = Conversation(user_id=inp.user_id, thread_id=inp.thread_id)
    _SESSIONS[conv.thread_id] = conv
    return _payload(conv, conv.send(inp.message))


@app.post("/confirm")
def confirm(inp: ConfirmIn) -> dict:
    conv = _SESSIONS.get(inp.thread_id) or resume_existing(inp.thread_id, inp.user_id)
    _SESSIONS[conv.thread_id] = conv
    return _payload(conv, conv.confirm(inp.decision))


@app.get("/trace/{session}")
def get_trace(session: str) -> dict:
    for conv in _SESSIONS.values():
        if conv.trace.session_id == session:
            return conv.trace.to_dict()
    return {"error": "session not found"}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_WEB / "index.html"))


if _WEB.exists():
    app.mount("/static", StaticFiles(directory=str(_WEB)), name="static")
