"""Write-operation guardrails (BUSINESS_RULES §4). Defense-in-depth: we re-verify
policy in code rather than trusting the model. Decides one of:

- allow:    safe to execute now (no extra friction)
- confirm:  eligible low-value -> require explicit user confirmation (HITL)
- escalate: high-value / defective / ineligible-but-disputed -> human handoff
- block:    parameters invalid / clearly ineligible -> refuse, explain
"""
from __future__ import annotations

from dataclasses import dataclass, field

from retailcare.policy import store
from retailcare.tools.impl import (
    ToolError,
    check_return_eligibility,
    issued_compensation_total,
)
from retailcare.tools.schema import CheckReturnEligibilityIn


@dataclass
class GuardDecision:
    action: str  # allow | confirm | escalate | block
    reason: str
    refund_amount: float = 0.0
    policy_versions: list[str] = field(default_factory=list)

    def as_tool_payload(self) -> dict:
        return {
            "guardrail": self.action,
            "reason": self.reason,
            "refund_amount": self.refund_amount,
            "policy_versions": self.policy_versions,
        }


def guard_write(name: str, args: dict) -> GuardDecision:
    if name == "create_return_request":
        return _guard_return(args)
    if name == "issue_compensation":
        return _guard_compensation(args)
    return GuardDecision("allow", "no guardrail for this tool")


def _guard_return(args: dict) -> GuardDecision:
    for f in ("user_id", "order_id", "item_id", "reason"):
        if not args.get(f):
            return GuardDecision("block", f"missing required field: {f}")
    if not args.get("idempotency_key"):
        return GuardDecision("block", "missing idempotency_key for write operation")
    try:
        elig = check_return_eligibility(CheckReturnEligibilityIn(
            user_id=args["user_id"], order_id=args["order_id"], item_id=args["item_id"],
            reason=args["reason"]))
    except ToolError as e:
        return GuardDecision("block", str(e))
    if not elig.eligible:
        return GuardDecision("block", f"{elig.reason_code}: {elig.explanation}",
                             policy_versions=elig.policy_versions)
    if elig.requires_human:
        return GuardDecision("escalate", f"high-value refund requires human review (RET-003): "
                             f"${elig.refund_amount}", elig.refund_amount, elig.policy_versions)
    return GuardDecision("confirm", "eligible low-value refund — confirm with customer",
                         elig.refund_amount, elig.policy_versions)


def _guard_compensation(args: dict) -> GuardDecision:
    if not args.get("idempotency_key"):
        return GuardDecision("block", "missing idempotency_key for write operation")
    amount = float(args.get("amount") or 0)
    if amount >= store.COMP_SINGLE_THRESHOLD:
        return GuardDecision("escalate", f"compensation ≥ {store.COMP_SINGLE_THRESHOLD:g} USD "
                             f"requires human approval (COMP-001): ${amount}",
                             amount, [store.POLICY_VERSION])
    # Cumulative cap: many sub-threshold payouts must not add up past the limit.
    prior = issued_compensation_total(args.get("user_id", ""),
                                      exclude_key=args.get("idempotency_key"))
    if prior + amount > store.COMP_CUMULATIVE_CAP:
        return GuardDecision("escalate", f"cumulative goodwill would exceed "
                             f"${store.COMP_CUMULATIVE_CAP:g} (COMP-001): ${prior:g} already "
                             f"issued + ${amount:g}", amount, [store.POLICY_VERSION])
    return GuardDecision("confirm", "goodwill compensation under cap — confirm with customer",
                         amount, [store.POLICY_VERSION])
