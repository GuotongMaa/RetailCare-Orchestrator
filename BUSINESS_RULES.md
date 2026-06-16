# RetailCare — Business Rules & After-Sales Policy

> **Authoritative, versioned policy.** The agent must ground every refund/return/
> compensation decision in these rules (retrieved via policy RAG, cited by chunk id +
> version into the trace). Code-enforced thresholds live in `src/retailcare/policy/store.py`
> and MUST stay in sync with this document.

**Policy version:** `2026.06`

---

## 1. Returns & Refunds

| id | rule |
|---|---|
| **RET-001** | Items may be returned within **30 days of delivery** for a full refund, if in original condition. |
| **RET-002** | **Non-returnable**: final-sale products, gift cards, and perishable goods. No return or refund. |
| **RET-003** | **High-value refunds ≥ 200 USD require human review** before they are issued. Never auto-approve. |
| **RET-004** | Defective/damaged items: eligible for full refund even outside the window, but **route to a human** for verification. |

## 2. Shipping

| id | rule |
|---|---|
| **SHIP-001** | If a shipment is marked `exception` or lost in transit, the customer may request a replacement or refund **after 7 days**. |

## 3. Compensation (goodwill)

| id | rule |
|---|---|
| **COMP-001** | Goodwill compensation (coupons/credits) **under 20 USD** may be offered for service failures; larger amounts require human approval. |

---

## 4. High-risk write operations — control flow (hero: refund)

Every **write** (`create_return_request`, `issue_compensation`) MUST pass this gate:

1. **Parameter completeness** — all required fields present; if missing (e.g. which item), **clarify**, do not guess.
2. **Policy check** — eligibility verified against RET-001..004 / RET via `check_return_eligibility`.
3. **Confirmation or escalation**
   - Eligible **and** low-value (< 200) **and** not defective → **ask the customer to confirm**, then execute (HITL confirm).
   - High-value (≥ 200) / defective / out-of-window dispute / policy conflict / uncertainty → **escalate_to_human**, do **not** execute.
4. **Idempotency** — returns dedup on `(order_id, item_id)`; compensation dedups on `idempotency_key`. Retries/double-clicks never double-act.
5. **Audit** — every attempt (including dedup hits and escalations) writes an audit-log row + trace event.

## 5. Fault handling (degrade safely, never lose money)

On tool timeout / error / stale data: **retry (bounded) → fallback message → escalate_to_human**. Never silently issue a refund on uncertain state.

## 6. Escalation discipline

Escalate when genuinely warranted (high-value, defective, dispute, repeated failure). Do **not** over-escalate trivial read-only questions (tracked by `unnecessary_handoff_rate`).
