"""Trust-boundary security tests (deterministic, no model calls).

These are the regression net for the IDOR fix (D2) and system-owned idempotency (D3):
a malicious / hallucinated tool argument from the model must NOT be able to act on
another customer, and the model's idempotency_key must be ignored in favour of a
system-derived one.
"""
import json

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from retailcare.data.db import session_scope
from retailcare.data.models import Compensation, Ticket
from retailcare.data.seed import seed
from retailcare.graph.agent import tools_node
from retailcare.graph.state import AgentState


@pytest.fixture(autouse=True)
def _seed():
    seed(reset=True)


def _tools_graph():
    g = StateGraph(AgentState)
    g.add_node("tools", tools_node)
    g.add_edge(START, "tools")
    g.add_edge("tools", END)
    return g.compile(checkpointer=MemorySaver())


def _run(session_user, name, model_args, auto_confirm=True, thread_id="t-sec"):
    tc = {"id": "c1", "type": "function",
          "function": {"name": name, "arguments": json.dumps(model_args)}}
    state = {"messages": [{"role": "assistant", "content": "", "tool_calls": [tc]}],
             "user_id": session_user, "thread_id": thread_id,
             "meta": {"auto_confirm": auto_confirm}}
    res = _tools_graph().invoke(state, {"configurable": {"thread_id": thread_id}})
    return json.loads(res["messages"][-1]["content"])


def test_injected_user_id_overrides_model_supplied_foreign_id():
    # Session is u1; the model tries to read u2's order O1002 and even forges user_id=u2.
    payload = _run("u1", "get_order", {"user_id": "u2", "order_id": "O1002"})
    assert "error" in payload
    assert "not found or not accessible" in payload["error"]


def test_session_user_can_read_own_order():
    payload = _run("u1", "get_order", {"user_id": "u2", "order_id": "O1001"})
    assert payload.get("user_id") == "u1"  # scoped to session user, not the forged one
    assert {i["item_id"] for i in payload["items"]} == {"I1", "I2"}


def test_missing_session_user_fails_closed():
    payload = _run(None, "get_order", {"order_id": "O1001"})
    assert "error" in payload and "no authenticated user" in payload["error"]


def test_cross_user_write_is_blocked():
    # u1 tries to create a return on u2's high-value laptop — must not write.
    payload = _run("u1", "create_return_request",
                   {"user_id": "u2", "order_id": "O1002", "item_id": "I4",
                    "reason": "x", "idempotency_key": "model-key"})
    # Denied either at the guardrail (block) or execution (error) — never written.
    assert payload.get("error") or payload.get("blocked")
    assert "not found or not accessible" in (payload.get("error") or payload.get("reason", ""))
    with session_scope() as s:
        assert s.query(Ticket).filter(Ticket.order_id == "O1002").count() == 0


def test_model_idempotency_key_is_ignored_no_double_write():
    # Two runs, different model-supplied keys, same logical action -> one ticket.
    a = _run("u1", "create_return_request",
             {"user_id": "u1", "order_id": "O1001", "item_id": "I1",
              "reason": "size", "idempotency_key": "model-key-1"})
    b = _run("u1", "create_return_request",
             {"user_id": "u1", "order_id": "O1001", "item_id": "I1",
              "reason": "size", "idempotency_key": "model-key-2-different"})
    assert a["ticket_id"] == b["ticket_id"]
    assert b["deduped"] is True
    # the persisted key must be the system-derived one, not either model key
    assert a["idempotency_key"].startswith("idem-")
    with session_scope() as s:
        assert s.query(Ticket).filter(Ticket.order_id == "O1001",
                                      Ticket.item_id == "I1").count() == 1


def test_compensation_no_double_spend_on_int_vs_float_amount():
    # QA regression: the model emits the same logical $15 comp as int then float;
    # the system-derived key must dedup to a single payout.
    a = _run("u1", "issue_compensation",
             {"user_id": "u1", "reason": "delay", "amount": 15, "idempotency_key": "m1"},
             thread_id="t-comp")
    b = _run("u1", "issue_compensation",
             {"user_id": "u1", "reason": "delay", "amount": 15.0, "idempotency_key": "m2"},
             thread_id="t-comp")
    assert a["comp_id"] == b["comp_id"]
    assert b["deduped"] is True
    with session_scope() as s:
        rows = s.query(Compensation).filter(Compensation.user_id == "u1").all()
        assert len(rows) == 1
        assert sum(r.amount for r in rows) == 15.0
