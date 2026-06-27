"""Structured JSON trace — every tool call / interrupt / failure is logged.

One trace = one conversation/session. Events are appended as JSON lines and the
full trace can be dumped as a single JSON object for the web UI and the eval
error-taxonomy pipeline (project definition v1 §4, §9).
"""
from __future__ import annotations

import contextvars
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

_TRACE_DIR = Path("trace_logs")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_SENSITIVE_KEYS = {
    "api_key", "apikey", "authorization", "password", "secret", "token",
    "access_token", "refresh_token", "session_token",
}

# Current trace for the in-flight graph run. Kept out of graph state so the
# checkpointer only ever serializes plain JSON-able values.
_CURRENT: contextvars.ContextVar[Trace | None] = contextvars.ContextVar(
    "current_trace", default=None
)


def set_current(trace: Trace | None) -> None:
    _CURRENT.set(trace)


def get_current() -> Trace | None:
    return _CURRENT.get()


@dataclass
class TraceEvent:
    kind: str  # tool_call | tool_result | tool_error | interrupt | decision | message
    name: str
    payload: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


@dataclass
class Trace:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    events: list[TraceEvent] = field(default_factory=list)

    def log(self, kind: str, name: str, **payload) -> None:
        self.events.append(TraceEvent(kind=kind, name=name,
                                      payload=_redact(_jsonable(payload))))

    # convenience helpers
    def tool_call(self, name: str, args: dict) -> None:
        self.log("tool_call", name, args=args)

    def tool_result(self, name: str, result: dict) -> None:
        self.log("tool_result", name, result=result)

    def tool_error(self, name: str, error: str, **extra) -> None:
        self.log("tool_error", name, error=error, **extra)

    def interrupt(self, name: str, **payload) -> None:
        self.log("interrupt", name, **payload)

    def decision(self, name: str, **payload) -> None:
        self.log("decision", name, **payload)

    def to_dict(self) -> dict:
        return {"session_id": self.session_id, "events": [asdict(e) for e in self.events]}

    def save(self, directory: Path = _TRACE_DIR) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str))
        return path


def _jsonable(obj):
    """Best-effort convert pydantic models / datetimes to JSON-safe structures."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _redact(obj):
    """Redact common secrets/PII before traces are stored or exposed."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k).lower()
            out[k] = "[REDACTED]" if key in _SENSITIVE_KEYS else _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, str):
        obj = _EMAIL_RE.sub("[REDACTED_EMAIL]", obj)
        return _PHONE_RE.sub("[REDACTED_PHONE]", obj)
    return obj
