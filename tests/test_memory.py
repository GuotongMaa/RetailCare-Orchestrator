"""Ticket-summary memory derivation (deterministic, no model/DB)."""
from retailcare.memory.summary import summarize_trace
from retailcare.trace.logger import Trace


def test_summary_ticket_created():
    tr = Trace()
    tr.tool_call("check_return_eligibility", {"order_id": "O1001", "item_id": "I1", "reason": "size"})
    tr.tool_result("check_return_eligibility",
                   {"reason_code": "ok", "refund_amount": 29.0, "policy_versions": ["2026.06"]})
    tr.tool_call("create_return_request",
                 {"order_id": "O1001", "item_id": "I1", "reason": "size", "idempotency_key": "k"})
    tr.tool_result("create_return_request", {"ticket_id": "T123", "refund_amount": 29.0})
    s = summarize_trace(tr)
    assert s.order_id == "O1001" and s.item_id == "I1"
    assert s.eligibility == "ok" and s.refund_amount == 29.0
    assert s.outcome == "ticket_created" and s.ticket_id == "T123"
    assert "ticket=T123" in s.render()


def test_summary_escalated():
    tr = Trace()
    tr.tool_call("check_return_eligibility", {"order_id": "O1002", "item_id": "I4", "reason": "defective"})
    tr.tool_result("check_return_eligibility", {"reason_code": "defective_review", "refund_amount": 884.0})
    tr.tool_call("escalate_to_human", {"user_id": "u2", "reason": "defective", "transcript": "..."})
    tr.tool_result("escalate_to_human", {"handoff_id": "H1"})
    s = summarize_trace(tr)
    assert s.outcome == "escalated" and s.refund_amount == 884.0


def test_summary_empty():
    assert summarize_trace(Trace()).render() == "No active ticket."
