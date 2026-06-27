"""Pydantic I/O contracts for the 8 tools (project definition v1 §5).

Read tools (low risk, auto-exec): get_order, get_shipment, search_policy,
get_coupon, check_return_eligibility.
Write tools (high risk: validation + policy check + confirm/escalate + idempotency
+ audit): create_return_request, issue_compensation, escalate_to_human.

`idempotency_key` is mandatory on every write tool's input.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ----------------------------- shared -----------------------------


class ItemView(BaseModel):
    item_id: str
    sku: str
    name: str
    category: str
    price: float
    qty: int = 1
    delivered_at: datetime | None = None
    returnable_until: datetime | None = None
    # Derived from any return ticket for this (order_id, item_id):
    # None | "return_requested" | "refunded" — keeps a follow-up status query fresh.
    return_status: str | None = None


# ----------------------------- read I/O -----------------------------


class GetOrderIn(BaseModel):
    user_id: str
    order_id: str


class OrderView(BaseModel):
    order_id: str
    user_id: str
    status: str
    currency: str
    total_amount: float
    created_at: datetime
    items: list[ItemView] = Field(default_factory=list)


class GetShipmentIn(BaseModel):
    user_id: str
    order_id: str


class ShipmentView(BaseModel):
    order_id: str
    carrier: str
    tracking_no: str
    status: str
    last_update: datetime
    eta: datetime | None = None


class SearchPolicyIn(BaseModel):
    query: str
    k: int = 3


class PolicyChunk(BaseModel):
    chunk_id: str
    text: str
    version: str  # versioned citation written into trace
    score: float = 0.0


class GetCouponIn(BaseModel):
    user_id: str


class CouponView(BaseModel):
    coupon_id: str
    code: str
    kind: str
    value: float
    status: str
    expires_at: datetime | None = None


class CheckReturnEligibilityIn(BaseModel):
    user_id: str
    order_id: str
    item_id: str
    reason: str


class Eligibility(BaseModel):
    eligible: bool
    reason_code: str  # ok / out_of_window / non_returnable_category / not_delivered / unknown_item
    explanation: str
    refund_amount: float = 0.0
    requires_human: bool = False
    policy_versions: list[str] = Field(default_factory=list)


# ----------------------------- write I/O -----------------------------


class CreateReturnRequestIn(BaseModel):
    user_id: str
    order_id: str
    item_id: str
    reason: str
    idempotency_key: str = Field(..., min_length=1)


class Ticket(BaseModel):
    ticket_id: str
    order_id: str
    item_id: str
    reason: str
    refund_amount: float
    status: str
    idempotency_key: str
    created_at: datetime
    deduped: bool = False  # True if returned an existing ticket (idempotent hit)


class IssueCompensationIn(BaseModel):
    user_id: str
    reason: str
    amount: float = Field(..., ge=0)
    idempotency_key: str = Field(..., min_length=1)


class CompensationResult(BaseModel):
    comp_id: str
    user_id: str
    reason: str
    amount: float
    status: str
    idempotency_key: str
    created_at: datetime
    deduped: bool = False


class EscalateToHumanIn(BaseModel):
    user_id: str
    reason: str
    transcript: str


class Handoff(BaseModel):
    handoff_id: str
    user_id: str
    reason: str
    status: str = "queued"
    created_at: datetime
