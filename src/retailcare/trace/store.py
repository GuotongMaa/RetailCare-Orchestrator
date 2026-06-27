"""Durable trace store keyed by thread_id (D12).

The live Trace is an in-memory object on the Conversation; when the process restarts
the audit trail would be lost. A system that claims auditability must persist it. We
write one redacted JSON envelope per ticket (thread_id), carrying the owning user_id
so `/trace` can enforce ownership even after a restart. Best-effort: persistence
failures never break a turn.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from retailcare.trace.logger import Trace

_DIR = Path("trace_logs")
_SAFE = re.compile(r"[^A-Za-z0-9._-]")


def _path(thread_id: str) -> Path:
    return _DIR / f"thread-{_SAFE.sub('_', thread_id)}.json"


def save(thread_id: str, user_id: str, trace: Trace) -> Path:
    _DIR.mkdir(parents=True, exist_ok=True)
    record = {"thread_id": thread_id, "user_id": user_id, **trace.to_dict()}
    path = _path(thread_id)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str))
    return path


def load(thread_id: str) -> dict | None:
    path = _path(thread_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())
