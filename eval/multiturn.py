"""Multi-turn / business-switch eval (P1): scripted multi-turn conversations on ONE
Conversation, scoring per-turn tool compliance AND state grounding — i.e. after the
user switches business (and switches back / across orders), does the agent act on the
RIGHT order. This is the end-to-end probe for the structured-state + digest layer (B);
single-turn datasets cannot exercise it.

    python -m eval.multiturn        # 1 run/task
    python -m eval.multiturn 2      # 2 runs/task
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.metrics import TaskAgg, aggregate_passk
from retailcare.config import settings, usage
from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation

DATASET = Path("eval/datasets/multiturn_tasks.jsonl")
REPORT = Path("reports/multiturn_report.md")


def load_tasks(path: Path = DATASET) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _turn_calls(conv: Conversation, start_idx: int) -> list[tuple[str, dict]]:
    return [(e.name, e.payload.get("args", {}) or {})
            for e in conv.trace.events[start_idx:] if e.kind == "tool_call"]


def run_task_once(task: dict) -> dict:
    conv = Conversation(user_id=task["user_id"], auto_confirm=True)
    turns_out: list[dict] = []
    for turn in task["turns"]:
        idx = len(conv.trace.events)
        error = None
        try:
            conv.send(turn["message"])
        except Exception as e:  # noqa: BLE001
            error = repr(e)
        calls = _turn_calls(conv, idx)
        names = {n for n, _ in calls}
        expect = set(turn.get("expect_tools", []))
        forbid = set(turn.get("forbid_tools", []))
        missing = expect - names
        violated = forbid & names
        # state grounding: tool calls this turn must target the expected order
        grounded = True
        if turn.get("expect_order"):
            orders = {a.get("order_id") for _, a in calls if a.get("order_id")}
            grounded = (turn["expect_order"] in orders) if orders else (not expect)
        ok = not error and not missing and not violated and grounded
        turns_out.append({"ok": ok, "called": sorted(names), "missing": sorted(missing),
                          "violated": sorted(violated), "grounded": grounded, "error": error})
    return {"task_id": task["id"], "intent": task.get("intent"),
            "success": all(t["ok"] for t in turns_out), "turns": turns_out}


def run(runs: int = 1) -> dict:
    usage.reset()
    tasks = load_tasks()
    per_task: dict[str, list[bool]] = {t["id"]: [] for t in tasks}
    last: dict[str, dict] = {}
    for _ in range(runs):
        seed(reset=True)
        for t in tasks:
            rec = run_task_once(t)
            per_task[t["id"]].append(rec["success"])
            last[t["id"]] = rec
    aggs = [TaskAgg(tid, len(s), sum(s)) for tid, s in per_task.items()]
    summary = {
        "model": settings.model, "runs_per_task": runs,
        **aggregate_passk(aggs, max_k=runs),
        "grounding_failures": [tid for tid, rec in last.items()
                               if any(not t["grounded"] for t in rec["turns"])],
        "usage_total": usage.snapshot(),
    }
    _write_report(summary, per_task, last)
    return summary


def _write_report(summary: dict, per_task: dict, last: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    passk = " | ".join(f"{k}={summary[k]}" for k in summary if k.startswith("pass^"))
    rows = []
    for tid, rec in last.items():
        per = "".join("✅" if t["ok"] else "❌" for t in rec["turns"])
        rate = f"{sum(per_task[tid])}/{len(per_task[tid])}"
        rows.append(f"| {tid} | {rec['intent']} | {len(rec['turns'])} | {per} | {rate} |")
    L = [
        "# Multi-turn / Business-switch Report (state grounding, B)", "",
        f"- model: `{summary['model']}`  |  runs/task: {summary['runs_per_task']}  |  "
        f"tasks: {summary['n_tasks']}",
        f"- **pass@1 = {summary['pass@1']}** CI95 {summary['pass@1_ci95']}"
        + (f"  |  {passk}" if passk else ""),
        f"- state-grounding failures (acted on wrong order after a switch): "
        f"{summary['grounding_failures'] or 'none'}",
        f"- total usage: {summary['usage_total']}", "",
        "| task | intent | turns | per-turn | success |",
        "|---|---|---|---|---|",
        *rows, "",
        "> A task passes only if EVERY turn calls the required tools, avoids forbidden ones, "
        "and targets the expected order — so a business switch (or switch-back) that loses the "
        "focus order fails the task. Exercises the digest/focus-stack (D1/D8).", "",
    ]
    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = run(runs=runs)
    print(json.dumps(out, indent=2))
    print(f"\n📄 report: {REPORT}")
