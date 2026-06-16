"""CLI: run the 5 after-sales intents end-to-end against the real model.

    python -m retailcare.cli            # run the 5-intent smoke suite
    python -m retailcare.cli chat u1    # interactive multi-turn chat as user u1
"""
from __future__ import annotations

import sys

from retailcare.config import usage
from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation

SCENARIOS = [
    ("order status", "u1", "What is the status of my order O1001?"),
    ("shipping", "u3", "Where is my package? My order id is O1003."),
    ("returns/refund (low value, eligible)", "u1",
     "I want to return item I1 in order O1001 — it's the wrong size."),
    ("coupons", "u1", "What coupons do I have available?"),
    ("escalation (high-value/defective)", "u2",
     "My laptop, item I4 in order O1002, arrived defective. I want a full refund."),
]


def _print_tools(conv: Conversation) -> None:
    calls = [e for e in conv.trace.events if e.kind in ("tool_call", "tool_error")]
    for e in calls:
        if e.kind == "tool_call":
            print(f"    🔧 {e.name}({e.payload.get('args')})")
        else:
            print(f"    ⚠️  {e.name} error: {e.payload.get('error')}")


def run_suite() -> int:
    seed(reset=True)
    usage.reset()
    failures = 0
    for i, (intent, user_id, text) in enumerate(SCENARIOS, 1):
        print(f"\n=== [{i}] {intent} — user {user_id} ===")
        print(f"  👤 {text}")
        conv = Conversation(user_id=user_id)
        try:
            reply = conv.send(text)
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ EXCEPTION: {e!r}")
            failures += 1
            continue
        _print_tools(conv)
        print(f"  🤖 {reply}")
        path = conv.trace.save()
        if not reply.strip():
            print("  ⚠️  empty reply")
            failures += 1
        print(f"  📄 trace: {path}")
    print(f"\n--- usage: {usage.snapshot()} ---")
    print("✅ suite passed" if failures == 0 else f"❌ {failures} scenario(s) failed")
    return 1 if failures else 0


def chat(user_id: str) -> int:
    seed(reset=False)
    conv = Conversation(user_id=user_id)
    print(f"chat as {user_id} (ctrl-c to exit)")
    while True:
        try:
            text = input("👤 ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        print(f"🤖 {conv.send(text)}")
    conv.trace.save()
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "chat":
        sys.exit(chat(sys.argv[2] if len(sys.argv) > 2 else "u1"))
    sys.exit(run_suite())
