"""Policy store + business rules.

M1: versioned policy chunks + a naive keyword retriever (good enough to wire
search_policy and write versions into trace). M2 swaps the retriever for Chroma
RAG and externalizes the prose into BUSINESS_RULES.md, keeping these chunk
versions as the source of truth for citations.
"""
from __future__ import annotations

from retailcare.tools.schema import PolicyChunk

# ----------------------------- business rules (code-enforced) -----------------------------
POLICY_VERSION = "2026.06"
RETURN_WINDOW_DAYS = 30
# Refunds at/above this amount must NOT be auto-approved — require human escalation.
HIGH_VALUE_THRESHOLD = 200.0
NON_RETURNABLE_CATEGORIES = {"final_sale", "gift_card", "perishable"}
# Goodwill compensation (COMP-001): a single payout at/above this needs human approval,
# AND the per-customer rolling total of issued goodwill may not exceed the cumulative cap
# (stops many sub-threshold payouts from adding up past the limit).
COMP_SINGLE_THRESHOLD = 20.0
COMP_CUMULATIVE_CAP = 50.0

# ----------------------------- policy corpus (versioned) -----------------------------
_CHUNKS: list[PolicyChunk] = [
    PolicyChunk(chunk_id="RET-001", version=POLICY_VERSION,
                text=("Standard return window: items may be returned within 30 days of delivery "
                      "for a full refund, provided they are in original condition.")),
    PolicyChunk(chunk_id="RET-002", version=POLICY_VERSION,
                text=("Non-returnable items: final-sale products, gift cards, and perishable "
                      "goods cannot be returned or refunded.")),
    PolicyChunk(chunk_id="RET-003", version=POLICY_VERSION,
                text=("High-value refunds: any refund of 200 USD or more requires manual review "
                      "by a human agent before it can be issued.")),
    PolicyChunk(chunk_id="RET-004", version=POLICY_VERSION,
                text=("Defective or damaged items are eligible for a full refund even outside the "
                      "standard window; route to a human agent for verification.")),
    PolicyChunk(chunk_id="SHIP-001", version=POLICY_VERSION,
                text=("Shipment exceptions: if a package is marked 'exception' or lost in transit, "
                      "the customer may request a replacement or refund after 7 days.")),
    PolicyChunk(chunk_id="COMP-001", version=POLICY_VERSION,
                text=("Goodwill compensation (coupons/credits) under 20 USD may be offered for "
                      "service failures; larger amounts require human approval.")),
]


def search(query: str, k: int = 3) -> list[PolicyChunk]:
    """Naive lexical overlap scorer (M1). Deterministic, no network."""
    q = {w for w in query.lower().split() if len(w) > 2}
    scored = []
    for c in _CHUNKS:
        words = set(c.text.lower().split())
        overlap = len(q & words)
        if overlap:
            scored.append(c.model_copy(update={"score": float(overlap)}))
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:k] or [_CHUNKS[0].model_copy(update={"score": 0.0})]


def all_versions() -> list[str]:
    return sorted({c.version for c in _CHUNKS})
