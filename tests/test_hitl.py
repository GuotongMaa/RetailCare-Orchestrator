"""HITL + guardrails (deterministic, no model calls).

Builds a tools-only graph and feeds it a crafted assistant tool_call, so we test
interrupt -> confirm/deny -> execute, plus the guardrail routing, without the LLM.
"""
import json

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from retailcare.data.db import session_scope
from retailcare.data.models import Ticket
from retailcare.data.seed import seed
from retailcare.graph.agent import tools_node
from retailcare.graph.guardrails import guard_write
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


def _state(name, args, auto_confirm=False):
    tc = {"id": "c1", "type": "function",
          "function": {"name": name, "arguments": json.dumps(args)}}
    # user_id/thread_id are trusted session state; tools_node injects them (D2/D3).
    return {"messages": [{"role": "assistant", "content": "", "tool_calls": [tc]}],
            "user_id": args.get("user_id"), "thread_id": "t-hitl",
            "meta": {"auto_confirm": auto_confirm}}


def _tickets(order_id, item_id):
    with session_scope() as s:
        return s.query(Ticket).filter(Ticket.order_id == order_id, Ticket.item_id == item_id).count()


# ---- guardrail routing (pure) ----

def test_guard_low_value_confirm():
    d = guard_write("create_return_request",
                    {"user_id": "u1", "order_id": "O1001", "item_id": "I1",
                     "reason": "size", "idempotency_key": "k"})
    assert d.action == "confirm" and d.refund_amount == 29.0


def test_guard_high_value_escalate():
    d = guard_write("create_return_request",
                    {"user_id": "u2", "order_id": "O1002", "item_id": "I4",
                     "reason": "defective", "idempotency_key": "k"})
    assert d.action == "escalate"


def test_guard_non_returnable_block():
    d = guard_write("create_return_request",
                    {"user_id": "u1", "order_id": "O1001", "item_id": "I2",
                     "reason": "x", "idempotency_key": "k"})
    assert d.action == "block"


def test_guard_missing_idempotency_block():
    d = guard_write("create_return_request",
                    {"user_id": "u1", "order_id": "O1001", "item_id": "I1",
                     "reason": "size", "idempotency_key": ""})
    assert d.action == "block"


# ---- interrupt / resume ----

def test_hitl_interrupt_then_confirm_executes():
    graph = _tools_graph()
    cfg = {"configurable": {"thread_id": "t-confirm"}}
    args = {"user_id": "u1", "order_id": "O1001", "item_id": "I1", "reason": "size",
            "idempotency_key": "k1"}
    res = graph.invoke(_state("create_return_request", args), cfg)
    assert res.get("__interrupt__"), "expected HITL interrupt"
    assert _tickets("O1001", "I1") == 0, "must not write before confirmation"

    res2 = graph.invoke(Command(resume="yes"), cfg)
    payload = json.loads(res2["messages"][-1]["content"])
    assert payload["ticket_id"] and payload["refund_amount"] == 29.0
    assert _tickets("O1001", "I1") == 1


def test_hitl_interrupt_then_deny_does_not_execute():
    graph = _tools_graph()
    cfg = {"configurable": {"thread_id": "t-deny"}}
    args = {"user_id": "u1", "order_id": "O1001", "item_id": "I1", "reason": "size",
            "idempotency_key": "k2"}
    graph.invoke(_state("create_return_request", args), cfg)
    res2 = graph.invoke(Command(resume="no"), cfg)
    payload = json.loads(res2["messages"][-1]["content"])
    assert payload.get("declined") is True
    assert _tickets("O1001", "I1") == 0


def test_hitl_logs_decisions_to_trace():
    """Regression: confirm path must log decisions without signature errors."""
    from retailcare.memory.summary import summarize_trace
    from retailcare.trace.logger import Trace, set_current

    tr = Trace()
    set_current(tr)
    try:
        graph = _tools_graph()
        cfg = {"configurable": {"thread_id": "t-trace"}}
        args = {"user_id": "u1", "order_id": "O1001", "item_id": "I1", "reason": "size",
                "idempotency_key": "kt"}
        graph.invoke(_state("create_return_request", args), cfg)
        graph.invoke(Command(resume="yes"), cfg)
    finally:
        set_current(None)
    kinds = {(e.kind, e.name) for e in tr.events}
    assert ("decision", "user_confirmed") in kinds
    assert summarize_trace(tr).outcome == "ticket_created"


def test_auto_confirm_executes_without_interrupt():
    graph = _tools_graph()
    cfg = {"configurable": {"thread_id": "t-auto"}}
    args = {"user_id": "u1", "order_id": "O1001", "item_id": "I1", "reason": "size",
            "idempotency_key": "k3"}
    res = graph.invoke(_state("create_return_request", args, auto_confirm=True), cfg)
    assert not res.get("__interrupt__")
    assert _tickets("O1001", "I1") == 1
