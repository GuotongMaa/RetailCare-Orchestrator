"""FastAPI session bookkeeping + auth trust boundary, without model calls."""
import pytest
from fastapi import HTTPException

from retailcare.api import app as appmod
from retailcare.api.app import _SESSIONS, _chat_conversation, _resume_conversation
from retailcare.api.auth import current_user, resolve_token
from retailcare.graph.runtime import Conversation


@pytest.fixture(autouse=True)
def _clear_sessions():
    _SESSIONS.clear()
    yield
    _SESSIONS.clear()


def test_chat_reuses_existing_thread_for_same_user():
    first = _chat_conversation("u1", "thread-1")
    second = _chat_conversation("u1", "thread-1")
    assert second is first


def test_thread_cannot_be_reused_by_another_user():
    _chat_conversation("u1", "thread-1")
    with pytest.raises(HTTPException) as exc:
        _chat_conversation("u2", "thread-1")
    assert exc.value.status_code == 403


def test_resume_reuses_existing_thread_for_same_user():
    first = _chat_conversation("u1", "thread-1")
    second = _resume_conversation("u1", "thread-1")
    assert second is first


# ---- auth trust boundary (D11) ----

def test_resolve_token_demo_scheme():
    assert resolve_token("demo-u1") == "u1"
    assert resolve_token("unknown") is None
    assert resolve_token("") is None


def test_current_user_rejects_missing_and_malformed():
    for header in (None, "", "Basic abc", "demo-u1", "Bearer notademo"):
        with pytest.raises(HTTPException) as exc:
            current_user(header)
        assert exc.value.status_code == 401


def test_current_user_resolves_valid_bearer():
    assert current_user("Bearer demo-u7") == "u7"


def test_trace_endpoint_enforces_ownership():
    conv = Conversation(user_id="u1", thread_id="t-own")
    _SESSIONS[conv.thread_id] = conv
    sid = conv.trace.session_id
    with pytest.raises(HTTPException) as exc:
        appmod.get_trace(sid, user_id="u2")
    assert exc.value.status_code == 403
    assert appmod.get_trace(sid, user_id="u1")["session_id"] == sid


def test_trace_endpoint_404_for_unknown_session():
    with pytest.raises(HTTPException) as exc:
        appmod.get_trace("no-such-session", user_id="u1")
    assert exc.value.status_code == 404


# ---- JWT production auth path (C6) ----

def _hs256_jwt(payload: dict, secret: str) -> str:
    import base64
    import hashlib
    import hmac
    import json

    def seg(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    head = seg({"alg": "HS256", "typ": "JWT"})
    body = seg(payload)
    sig = hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{head}.{body}.{sig_b64}"


def test_jwt_mode_accepts_valid_and_rejects_tampered(monkeypatch):
    monkeypatch.setenv("RETAILCARE_JWT_SECRET", "topsecret")
    good = _hs256_jwt({"sub": "u9"}, "topsecret")
    assert resolve_token(good) == "u9"
    # wrong secret -> rejected
    assert resolve_token(_hs256_jwt({"sub": "u9"}, "WRONG")) is None
    # tampered payload -> signature fails
    head, body, sig = good.split(".")
    assert resolve_token(f"{head}.{body}x.{sig}") is None
    # in JWT mode the demo scheme is disabled
    assert resolve_token("demo-u1") is None


def test_jwt_mode_rejects_expired_and_alg_none(monkeypatch):
    import base64
    import json
    monkeypatch.setenv("RETAILCARE_JWT_SECRET", "topsecret")
    assert resolve_token(_hs256_jwt({"sub": "u9", "exp": 0}, "topsecret")) is None

    def seg(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    none_tok = f"{seg({'alg': 'none'})}.{seg({'sub': 'u9'})}."
    assert resolve_token(none_tok) is None
