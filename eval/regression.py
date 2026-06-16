"""Model-free eval-regression gate (project definition v1 §9 'evals as unit tests').

Asserts the safety-critical guardrail decisions on a labeled set. Deterministic and
fast, so it runs on every CI push and turns the build RED if a policy regression is
introduced (e.g. high-value refunds stop escalating). No model calls, no secrets.

    python -m eval.regression   # exit 0 = baseline held, 1 = regression
"""
from __future__ import annotations

import sys

from retailcare.data.seed import seed
from retailcare.graph.guardrails import guard_write

# (order_id, item_id, reason, expected_guard_action)
CASES = [
    ("O1001", "I1", "wrong size", "confirm"),          # in-window low-value -> confirm
    ("O1005", "I9", "too big", "confirm"),             # $80 jacket -> confirm
    ("O1004", "I6", "dont like", "confirm"),           # $199 just under threshold
    ("O1004", "I7", "dont like", "escalate"),          # $201 just over -> escalate
    ("O1002", "I4", "defective", "escalate"),          # high-value + defective
    ("O1007", "I11", "defective", "escalate"),         # low-value but defective (RET-004)
    ("O1001", "I2", "changed mind", "block"),          # gift card / final-sale
    ("O1005", "I8", "changed mind", "block"),          # perishable
    ("O1002", "I3", "changed mind", "block"),          # out of window
    ("O1006", "I10", "changed mind", "block"),         # not delivered
]


def main() -> int:
    seed(reset=True)
    failures = []
    for order_id, item_id, reason, expected in CASES:
        d = guard_write("create_return_request", {
            "order_id": order_id, "item_id": item_id, "reason": reason, "idempotency_key": "x"})
        ok = d.action == expected
        print(f"  {'✅' if ok else '❌'} {order_id}/{item_id} ({reason}) -> "
              f"{d.action} (expected {expected})")
        if not ok:
            failures.append((order_id, item_id, expected, d.action))
    # compensation thresholds
    for amount, expected in ((5.0, "confirm"), (50.0, "escalate")):
        d = guard_write("issue_compensation",
                        {"user_id": "u1", "reason": "x", "amount": amount, "idempotency_key": "x"})
        ok = d.action == expected
        print(f"  {'✅' if ok else '❌'} compensation ${amount} -> {d.action} (expected {expected})")
        if not ok:
            failures.append(("comp", amount, expected, d.action))

    if failures:
        print(f"\n❌ REGRESSION: {len(failures)} guardrail decision(s) changed: {failures}")
        return 1
    print(f"\n✅ baseline held — {len(CASES) + 2} safety decisions correct")
    return 0


if __name__ == "__main__":
    sys.exit(main())
