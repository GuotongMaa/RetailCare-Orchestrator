"""End-to-end demo (`make demo`): the refund hero flow with real HITL + cross-session resume.

Scenario A: low-value refund -> guardrail asks to confirm -> interrupt() pauses ->
            user confirms -> idempotent execute -> receipt.
Scenario B: same ticket, but the user "comes back the next day" — a brand-new
            Conversation object (fresh process semantics) re-attaches to the persisted
            thread via the checkpointer and confirms, proving cross-session recovery.
"""
from __future__ import annotations

import uuid

from retailcare.config import usage
from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation, resume_existing
from retailcare.memory.summary import summarize_trace
from retailcare.trace.logger import Trace


def _banner(t: str) -> None:
    print(f"\n{'=' * 64}\n{t}\n{'=' * 64}")


def scenario_a() -> None:
    _banner("Scenario A — refund with HITL confirmation (single session)")
    conv = Conversation(user_id="u1")  # auto_confirm=False -> real interrupt
    res = conv.send("I want to return item I1 in order O1001, it's the wrong size.")
    while res.interrupted:
        print(f"  ⏸  HITL interrupt: {res.interrupt.get('prompt')}")
        print("  👤 (customer types) yes")
        res = conv.confirm("yes")
    print(f"  🤖 {res.reply}")
    print(f"  🧠 {summarize_trace(conv.trace).render()}")


def scenario_b() -> None:
    _banner("Scenario B — cross-session resume (customer returns next day)")
    thread = "ticket-" + uuid.uuid4().hex[:6]
    trace = Trace()
    day1 = Conversation(user_id="u4", thread_id=thread, trace=trace)
    res = day1.send("Please return the rain jacket I9 in order O1005, it's too big.")
    if not res.interrupted:
        print(f"  🤖 (no confirmation needed) {res.reply}")
        return
    print(f"  Day 1 ⏸  paused awaiting confirmation on thread '{thread}' — customer leaves.")

    # Next day: a NEW Conversation object re-attaches to the persisted thread.
    print("  ... next day, new session ...")
    day2 = resume_existing(thread_id=thread, user_id="u4", trace=trace)
    res = day2.confirm("yes")
    print(f"  Day 2 🤖 {res.reply}")
    print(f"  🧠 {summarize_trace(trace).render()}")


def main() -> int:
    seed(reset=True)
    usage.reset()
    scenario_a()
    scenario_b()
    print(f"\n--- usage: {usage.snapshot()} ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
