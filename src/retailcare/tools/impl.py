"""Tool implementations. Pure functions over the DB + policy store.

Read tools are side-effect free. Write tools enforce idempotency at the storage
layer and write an audit-log row. Business idempotency for returns is keyed on
(order_id, item_id) per project definition v1 §6, in addition to the
client-supplied idempotency_key.
"""
from __future__ import annotations

import uuid

from retailcare.data.db import session_scope
from retailcare.data.models import AuditLog, Compensation, Coupon, Order, Shipment, Ticket
from retailcare.policy import store
from retailcare.tools.schema import (
    CheckReturnEligibilityIn,
    CompensationResult,
    CouponView,
    CreateReturnRequestIn,
    Eligibility,
    EscalateToHumanIn,
    GetCouponIn,
    GetOrderIn,
    GetShipmentIn,
    Handoff,
    IssueCompensationIn,
    ItemView,
    OrderView,
    PolicyChunk,
    SearchPolicyIn,
    ShipmentView,
)
from retailcare.tools.schema import (
    Ticket as TicketView,
)


class ToolError(Exception):
    """Raised for not-found / invalid-state conditions (distinct from validation errors)."""


# Defect keywords -> RET-004 (defective items need human verification, any value).
_DEFECT_WORDS = ("defective", "damaged", "broken", "faulty", "defect", "cracked",
                 "not working", "doesn't work", "stopped working", "won't turn on")


# ----------------------------- read tools -----------------------------


def get_order(inp: GetOrderIn) -> OrderView:
    with session_scope() as s:
        o = s.get(Order, inp.order_id)
        if not o:
            raise ToolError(f"order not found: {inp.order_id}")
        items = [ItemView(item_id=i.item_id, sku=i.sku, name=i.name, category=i.category,
                          price=i.price, qty=i.qty, delivered_at=i.delivered_at,
                          returnable_until=i.returnable_until) for i in o.items]
        return OrderView(order_id=o.order_id, user_id=o.user_id, status=o.status,
                         currency=o.currency, total_amount=o.total_amount,
                         created_at=o.created_at, items=items)


def get_shipment(inp: GetShipmentIn) -> ShipmentView:
    with session_scope() as s:
        sh = s.get(Shipment, inp.order_id)
        if not sh:
            raise ToolError(f"shipment not found for order: {inp.order_id}")
        return ShipmentView(order_id=sh.order_id, carrier=sh.carrier, tracking_no=sh.tracking_no,
                            status=sh.status, last_update=sh.last_update, eta=sh.eta)


def search_policy(inp: SearchPolicyIn) -> list[PolicyChunk]:
    from retailcare.policy import rag
    return rag.search(inp.query, k=inp.k)


def get_coupon(inp: GetCouponIn) -> list[CouponView]:
    with session_scope() as s:
        rows = s.query(Coupon).filter(Coupon.user_id == inp.user_id).all()
        return [CouponView(coupon_id=c.coupon_id, code=c.code, kind=c.kind, value=c.value,
                           status=c.status, expires_at=c.expires_at) for c in rows]


def check_return_eligibility(inp: CheckReturnEligibilityIn) -> Eligibility:
    versions = store.all_versions()
    with session_scope() as s:
        o = s.get(Order, inp.order_id)
        if not o:
            raise ToolError(f"order not found: {inp.order_id}")
        item = next((i for i in o.items if i.item_id == inp.item_id), None)
        if not item:
            return Eligibility(eligible=False, reason_code="unknown_item",
                               explanation=f"item {inp.item_id} not in order {inp.order_id}",
                               policy_versions=versions)
        if item.delivered_at is None:
            return Eligibility(eligible=False, reason_code="not_delivered",
                               explanation="item not delivered yet; cannot start a return",
                               policy_versions=versions)
        if item.category in store.NON_RETURNABLE_CATEGORIES:
            return Eligibility(eligible=False, reason_code="non_returnable_category",
                               explanation=f"category '{item.category}' is non-returnable (RET-002)",
                               policy_versions=versions)
        from retailcare.data.seed import NOW
        if item.returnable_until is None or item.returnable_until < NOW:
            return Eligibility(eligible=False, reason_code="out_of_window",
                               explanation="return window (30 days) has closed (RET-001)",
                               policy_versions=versions)
        refund = item.price * item.qty
        if any(w in inp.reason.lower() for w in _DEFECT_WORDS):
            return Eligibility(
                eligible=True, reason_code="defective_review",
                explanation="defective/damaged item requires human verification (RET-004)",
                refund_amount=refund, requires_human=True, policy_versions=versions)
        high = refund >= store.HIGH_VALUE_THRESHOLD
        return Eligibility(
            eligible=True, reason_code="ok",
            explanation=("eligible for refund"
                         + (" but high-value: requires human review (RET-003)" if high else "")),
            refund_amount=refund, requires_human=high, policy_versions=versions)


# ----------------------------- write tools -----------------------------


def _audit(s, action: str, detail: str) -> None:
    s.add(AuditLog(action=action, detail=detail))


def create_return_request(inp: CreateReturnRequestIn) -> TicketView:
    """Idempotent: dedups on (order_id, item_id). Returns existing ticket if present."""
    with session_scope() as s:
        existing = (s.query(Ticket)
                    .filter(Ticket.order_id == inp.order_id, Ticket.item_id == inp.item_id)
                    .first())
        if existing:
            _audit(s, "create_return_request.dedup",
                   f"{inp.order_id}/{inp.item_id} -> {existing.ticket_id}")
            return _ticket_view(existing, deduped=True)

        elig = check_return_eligibility(CheckReturnEligibilityIn(
            order_id=inp.order_id, item_id=inp.item_id, reason=inp.reason))
        if not elig.eligible:
            raise ToolError(f"not eligible: {elig.reason_code} — {elig.explanation}")

        t = Ticket(ticket_id="T" + uuid.uuid4().hex[:8], order_id=inp.order_id,
                   item_id=inp.item_id, reason=inp.reason, refund_amount=elig.refund_amount,
                   status="created", idempotency_key=inp.idempotency_key)
        s.add(t)
        _audit(s, "create_return_request", f"{t.ticket_id} amount={t.refund_amount}")
        s.flush()
        return _ticket_view(t, deduped=False)


def issue_compensation(inp: IssueCompensationIn) -> CompensationResult:
    """Idempotent on idempotency_key."""
    with session_scope() as s:
        existing = (s.query(Compensation)
                    .filter(Compensation.idempotency_key == inp.idempotency_key).first())
        if existing:
            _audit(s, "issue_compensation.dedup", f"{inp.idempotency_key} -> {existing.comp_id}")
            return _comp_view(existing, deduped=True)
        c = Compensation(comp_id="K" + uuid.uuid4().hex[:8], user_id=inp.user_id,
                         reason=inp.reason, amount=inp.amount, status="issued",
                         idempotency_key=inp.idempotency_key)
        s.add(c)
        _audit(s, "issue_compensation", f"{c.comp_id} amount={c.amount}")
        s.flush()
        return _comp_view(c, deduped=False)


def escalate_to_human(inp: EscalateToHumanIn) -> Handoff:
    from datetime import datetime
    with session_scope() as s:
        _audit(s, "escalate_to_human", f"user={inp.user_id} reason={inp.reason[:60]}")
    return Handoff(handoff_id="H" + uuid.uuid4().hex[:8], user_id=inp.user_id,
                   reason=inp.reason, status="queued", created_at=datetime.utcnow())


# ----------------------------- view helpers -----------------------------


def _ticket_view(t: Ticket, deduped: bool) -> TicketView:
    return TicketView(ticket_id=t.ticket_id, order_id=t.order_id, item_id=t.item_id,
                      reason=t.reason, refund_amount=t.refund_amount, status=t.status,
                      idempotency_key=t.idempotency_key, created_at=t.created_at, deduped=deduped)


def _comp_view(c: Compensation, deduped: bool) -> CompensationResult:
    return CompensationResult(comp_id=c.comp_id, user_id=c.user_id, reason=c.reason,
                              amount=c.amount, status=c.status,
                              idempotency_key=c.idempotency_key, created_at=c.created_at,
                              deduped=deduped)
