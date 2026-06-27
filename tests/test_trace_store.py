"""Durable trace store (C4/D12): persistence, load, ownership after 'restart'."""
import pytest
from fastapi import HTTPException

from retailcare.api import app as appmod
from retailcare.trace import store
from retailcare.trace.logger import Trace


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DIR", tmp_path)


def test_save_and_load_roundtrip():
    tr = Trace()
    tr.tool_call("get_order", {"order_id": "O1001"})
    store.save("t-1", "u1", tr)
    rec = store.load("t-1")
    assert rec["user_id"] == "u1" and rec["thread_id"] == "t-1"
    assert rec["events"][0]["name"] == "get_order"


def test_load_missing_returns_none():
    assert store.load("no-such-thread") is None


def test_persisted_trace_keeps_redaction():
    tr = Trace()
    tr.log("message", "user", text="mail me at a@b.com", api_key="sk-secret")
    store.save("t-pii", "u1", tr)
    rec = store.load("t-pii")
    ev = rec["events"][0]["payload"]
    assert "a@b.com" not in ev["text"] and ev["api_key"] == "[REDACTED]"


def test_trace_by_thread_endpoint_enforces_ownership_after_restart():
    # Simulate restart: nothing in _SESSIONS, only the persisted record exists.
    store.save("t-own", "u1", Trace())
    with pytest.raises(HTTPException) as exc:
        appmod.get_trace_by_thread("t-own", user_id="u2")
    assert exc.value.status_code == 403
    assert appmod.get_trace_by_thread("t-own", user_id="u1")["thread_id"] == "t-own"
    with pytest.raises(HTTPException) as exc2:
        appmod.get_trace_by_thread("missing", user_id="u1")
    assert exc2.value.status_code == 404
