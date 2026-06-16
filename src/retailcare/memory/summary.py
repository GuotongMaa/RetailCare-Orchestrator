"""Ticket-state summary memory (project definition v1 §7).

Short-term memory = the message list persisted by the checkpointer. On top of it
we derive a compact, deterministic *ticket summary* from the trace ("confirmed
order X, reason=size, eligibility=ok $29, outcome=ticket T123") to control
long-context cost/forgetting and to show on the UI — without re-sending the whole
history to the model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from retailcare.trace.logger import Trace


@dataclass
class TicketSummary:
    order_id: str | None = None
    item_id: str | None = None
    reason: str | None = None
    eligibility: str | None = None          # ok / out_of_window / non_returnable_category / ...
    refund_amount: float | None = None
    outcome: str | None = None              # ticket_created / escalated / declined / blocked / none
    ticket_id: str | None = None
    policy_versions: list[str] | None = None

    def render(self) -> str:
        if not self.order_id and not self.outcome:
            return "No active ticket."
        bits = []
        if self.order_id:
            bits.append(f"order={self.order_id}")
        if self.item_id:
            bits.append(f"item={self.item_id}")
        if self.reason:
            bits.append(f"reason={self.reason}")
        if self.eligibility:
            bits.append(f"eligibility={self.eligibility}")
        if self.refund_amount is not None:
            bits.append(f"refund=${self.refund_amount}")
        if self.outcome:
            bits.append(f"outcome={self.outcome}")
        if self.ticket_id:
            bits.append(f"ticket={self.ticket_id}")
        return "Ticket summary: " + ", ".join(bits)

    def to_dict(self) -> dict:
        return asdict(self)


def summarize_trace(trace: Trace) -> TicketSummary:
    s = TicketSummary()
    for e in trace.events:
        p = e.payload or {}
        if e.kind == "tool_call" and e.name in ("check_return_eligibility", "create_return_request"):
            args = p.get("args", {})
            s.order_id = args.get("order_id", s.order_id)
            s.item_id = args.get("item_id", s.item_id)
            s.reason = args.get("reason", s.reason)
        if e.kind == "tool_result" and e.name == "check_return_eligibility":
            r = p.get("result", {})
            s.eligibility = r.get("reason_code", s.eligibility)
            if r.get("refund_amount"):
                s.refund_amount = r.get("refund_amount")
            s.policy_versions = r.get("policy_versions", s.policy_versions)
        if e.kind == "tool_result" and e.name == "create_return_request":
            r = p.get("result", {})
            s.outcome = "ticket_created"
            s.ticket_id = r.get("ticket_id", s.ticket_id)
            if r.get("refund_amount"):
                s.refund_amount = r.get("refund_amount")
        if e.kind == "tool_result" and e.name == "escalate_to_human":
            s.outcome = "escalated"
        if e.kind == "decision" and e.name == "user_declined":
            s.outcome = "declined"
        if e.kind == "decision" and p.get("action") == "block":
            s.outcome = s.outcome or "blocked"
    return s
