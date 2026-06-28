"""HITL end-to-end eval (P2): run real refund conversations with auto_confirm=False and
script the customer's yes/no, verifying the human-in-the-loop gate actually controls the
write — confirm -> ticket written, decline -> NOTHING written. The model-based suite
otherwise runs auto_confirm=True and never exercises this path.

    python -m eval.hitl_eval
"""
from __future__ import annotations

import json
from pathlib import Path

from retailcare.config import settings, usage
from retailcare.data.db import session_scope
from retailcare.data.models import Ticket
from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation

REPORT = Path("reports/hitl_report.md")

# Low-value, eligible items -> guardrail routes to `confirm` (HITL), not escalate/block.
SCENARIOS = [
    {"id": "H1", "user_id": "u1", "order_id": "O1001", "item_id": "I1", "decision": "yes",
     "expect_write": True, "message": "Return the t-shirt I1 in order O1001, it's the wrong size."},
    {"id": "H2", "user_id": "u1", "order_id": "O1001", "item_id": "I1", "decision": "no",
     "expect_write": False, "message": "Return the t-shirt I1 in order O1001, it's the wrong size."},
    {"id": "H3", "user_id": "u4", "order_id": "O1005", "item_id": "I9", "decision": "yes",
     "expect_write": True, "message": "Return the rain jacket I9 in order O1005, it's too big."},
    {"id": "H4", "user_id": "u4", "order_id": "O1005", "item_id": "I9", "decision": "no",
     "expect_write": False, "message": "Return the rain jacket I9 in order O1005, it's too big."},
]


def _ticket_exists(order_id: str, item_id: str) -> bool:
    with session_scope() as s:
        return s.query(Ticket).filter(Ticket.order_id == order_id,
                                      Ticket.item_id == item_id).count() > 0


def run_scenario(sc: dict) -> dict:
    seed(reset=True)  # isolate each scenario's DB state
    conv = Conversation(user_id=sc["user_id"], auto_confirm=False)
    error = None
    try:
        res = conv.send(sc["message"])
        interrupted = res.interrupted
        if interrupted:
            conv.confirm(sc["decision"])
    except Exception as e:  # noqa: BLE001
        return {"id": sc["id"], "interrupted": False, "wrote": False, "ok": False, "error": repr(e)}
    wrote = _ticket_exists(sc["order_id"], sc["item_id"])
    # correct = HITL gate fired AND the write matched the decision
    ok = interrupted and (wrote == sc["expect_write"])
    return {"id": sc["id"], "decision": sc["decision"], "interrupted": interrupted,
            "wrote": wrote, "expect_write": sc["expect_write"], "ok": ok, "error": error}


def run() -> dict:
    usage.reset()
    results = [run_scenario(sc) for sc in SCENARIOS]
    n = len(results)
    summary = {
        "model": settings.model, "n": n,
        "hitl_correct_rate": round(sum(r["ok"] for r in results) / n, 4) if n else 0.0,
        "interrupt_fired_rate": round(sum(r["interrupted"] for r in results) / n, 4) if n else 0.0,
        "results": results,
        "usage_total": usage.snapshot(),
    }
    _write_report(summary)
    return summary


def _write_report(summary: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rows = [f"| {r['id']} | {r.get('decision','-')} | {r['interrupted']} | {r['wrote']} | "
            f"{r.get('expect_write','-')} | {'✅' if r['ok'] else '❌'} |" for r in summary["results"]]
    L = [
        "# HITL End-to-End Report (confirm/decline controls the write)", "",
        f"- model: `{summary['model']}`  |  scenarios: {summary['n']}",
        f"- **hitl_correct_rate = {summary['hitl_correct_rate']}** "
        f"(interrupt fired AND write matched the decision)",
        f"- interrupt_fired_rate = {summary['interrupt_fired_rate']}",
        f"- total usage: {summary['usage_total']}", "",
        "| scenario | decision | interrupted | wrote | expected_write | ok |",
        "|---|---|---|---|---|---|",
        *rows, "",
        "> Run with `auto_confirm=False`: the agent must PAUSE at the write (HITL interrupt), "
        "then a 'no' must leave the DB untouched and a 'yes' must create exactly the ticket. "
        "Exercises the guardrail `confirm` route + resume path (and D7 token binding).", "",
    ]
    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2))
    print(f"\n📄 report: {REPORT}")
