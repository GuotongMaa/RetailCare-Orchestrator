"""State digest + tool-effect projection + system-derived idempotency.

Pure, deterministic, model-free — so it is unit-testable without the network.

- `render_digest(state)`  -> the one-shot text injected into the model each turn.
  It is a *projection* of the structured state, NEVER stored in `messages`
  (see docs/state-and-security-upgrade.md D1/D9). Capped to keep it cheap.
- `apply_tool_effect(...)` -> the structured-state updates derived from a real
  tool result (D5: the system maintains state from verified facts, not from what
  the model claims).
- `derive_idempotency_key(...)` -> deterministic write key owned by the system,
  not the model (D3), so retries within a ticket never double-act.
"""
from __future__ import annotations

import hashlib
import json

# Map a tool to the business intent it implies (None = intent-neutral, e.g. policy).
_TOOL_INTENT: dict[str, str | None] = {
    "get_order": "order_status",
    "get_shipment": "shipping",
    "search_policy": None,
    "get_coupon": "coupons",
    "check_return_eligibility": "returns",
    "create_return_request": "returns",
    "issue_compensation": "compensation",
    "escalate_to_human": "complaint",
}

_DIGEST_CHAR_CAP = 1200  # ~300 tokens (D9)
_STACK_CAP = 3


def intent_for_tool(name: str) -> str | None:
    return _TOOL_INTENT.get(name)


def derive_idempotency_key(thread_id: str | None, name: str, args: dict) -> str:
    """System-owned, deterministic per (ticket, customer, logical action). D3.

    The amount is normalised to a fixed-precision string so that `15` (int) and
    `15.0` (float) — which the model may emit interchangeably — map to ONE key,
    otherwise a retry could double-issue compensation. `user_id` is folded in as
    defence-in-depth so a missing thread_id can never collapse keys across
    customers. Note: within one ticket two genuinely-distinct comps that share
    (reason, amount) are intentionally treated as the same action (dedup wins over
    double-pay); a distinct payout should carry a distinct reason.
    """
    tid = thread_id or "anon"
    uid = args.get("user_id") or "anon"
    if name == "create_return_request":
        basis = (tid, uid, name, args.get("order_id"), args.get("item_id"))
    elif name == "issue_compensation":
        reason = (args.get("reason") or "").strip().lower()
        amount = f"{float(args.get('amount') or 0):.2f}"
        basis = (tid, uid, name, reason, amount)
    else:
        basis = (tid, uid, name, json.dumps(args, sort_keys=True, default=str))
    digest = hashlib.sha256(repr(basis).encode()).hexdigest()[:16]
    return f"idem-{digest}"


def action_token(thread_id: str | None, name: str, args: dict) -> str:
    """Fingerprint of a specific gated write, used to bind an HITL confirmation to
    the exact action the user saw (D7). Deterministic so a node re-run on resume
    recomputes the same token."""
    basis = (thread_id or "anon", name, json.dumps(args, sort_keys=True, default=str))
    return "act-" + hashlib.sha256(repr(basis).encode()).hexdigest()[:16]


def apply_tool_effect(state: dict, name: str, args: dict, result, error: str | None) -> dict:
    """Derive structured-state updates from one executed tool call.

    Returns a partial dict to merge into state. Reads current focus to manage the
    cross-order focus stack (D8). Only writes from *verified* tool facts (D5).
    """
    updates: dict = {}
    if error:
        return updates  # never advance state on an errored/blocked call

    new_intent = intent_for_tool(name)
    if new_intent:
        updates["intent"] = new_intent

    # ---- focus + shallow stack on order change (D8) ----
    order_id = args.get("order_id")
    if order_id:
        cur = state.get("focus") or {}
        if cur.get("order_id") and cur.get("order_id") != order_id:
            stack = list(state.get("focus_stack") or [])
            stack.append(cur)
            updates["focus_stack"] = stack[-_STACK_CAP:]
        focus = {"order_id": order_id}
        if args.get("item_id"):
            focus["item_id"] = args["item_id"]
        updates["focus"] = focus

    # ---- findings: cache verified eligibility, keyed by item (merge reducer) ----
    if name == "check_return_eligibility" and isinstance(result, dict):
        item_id = args.get("item_id")
        if item_id:
            updates["findings"] = {item_id: {
                "eligible": result.get("eligible"),
                "refund_amount": result.get("refund_amount"),
                "requires_human": result.get("requires_human"),
                "reason_code": result.get("reason_code"),
            }}

    # ---- terminal task status ----
    if name == "create_return_request" and isinstance(result, dict) and result.get("ticket_id"):
        updates["task_status"] = "resolved"
    elif name == "escalate_to_human":
        updates["task_status"] = "escalated"

    return updates


def render_digest(state: dict) -> str:
    """One-shot, capped projection of structured state for the model (D1/D9).

    Returns "" when there is nothing worth showing (e.g. first turn) so the agent
    node can skip injecting an empty block.
    """
    lines: list[str] = []

    intent = state.get("intent")
    if intent:
        prior = state.get("focus_stack") or []
        suffix = f" (prior: {prior[-1].get('order_id')})" if prior else ""
        lines.append(f"intent: {intent}{suffix}")

    focus = state.get("focus") or {}
    if focus:
        lines.append("focus: " + " ".join(f"{k}={v}" for k, v in focus.items()))

    # D9: only show findings relevant to the current focus item.
    findings = state.get("findings") or {}
    focus_item = focus.get("item_id")
    relevant = {focus_item: findings[focus_item]} if focus_item in findings else findings
    for item_id, f in list(relevant.items())[:3]:
        if not isinstance(f, dict):
            continue  # tolerate a malformed checkpoint — digest runs every turn
        elig = "eligible" if f.get("eligible") else "not-eligible"
        amt = f.get("refund_amount")
        human = " (needs human)" if f.get("requires_human") else ""
        lines.append(f"verified {item_id}: {elig} ${amt}{human} [{f.get('reason_code')}]")

    pending = state.get("pending_action")
    if pending:
        lines.append(f"pending: {pending.get('tool')} awaiting customer confirmation")

    status = state.get("task_status")
    if status:
        lines.append(f"status: {status}")

    plan = state.get("plan") or []
    if plan:
        steps = " ".join(f"[{'x' if s.get('status') == 'done' else ' '}]{s.get('step')}"
                         for s in plan[-6:] if isinstance(s, dict))
        lines.append(f"plan: {steps}")

    if not lines:
        return ""
    body = "\n".join(lines)
    if len(body) > _DIGEST_CHAR_CAP:
        body = body[:_DIGEST_CHAR_CAP] + "…"
    return "[current_state]\n" + body
