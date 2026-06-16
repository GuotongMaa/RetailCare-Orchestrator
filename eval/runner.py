"""Eval closed loop (M3): data -> run agent (multi-seed) -> trace -> metrics
(pass^k + CI + compliance) -> error taxonomy -> report.

    python -m eval.runner            # 1 run/task (pass@1 + CI), fast
    python -m eval.runner 5          # 5 runs/task -> pass^k consistency
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.common import RunConfig, run_task_once
from eval.error_taxonomy import aggregate as tax_aggregate
from eval.metrics import TaskAgg, aggregate_passk, compliance_metrics
from retailcare.config import settings, usage
from retailcare.data.seed import seed

DATASET = Path("eval/datasets/refund_tasks.jsonl")
REPORT = Path("reports/baseline_report.md")
_CFG = RunConfig("L1_default", guardrails=True, auto_confirm=True, policy_mode="prompt")


def load_tasks(path: Path = DATASET) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run(runs: int = 1) -> dict:
    usage.reset()
    tasks = load_tasks()
    records: list[dict] = []
    per_task: dict[str, list[bool]] = {t["id"]: [] for t in tasks}
    for _ in range(runs):
        seed(reset=True)
        for t in tasks:
            rec = run_task_once(t, _CFG)
            records.append(rec)
            per_task[t["id"]].append(rec["success"])
    aggs = [TaskAgg(tid, len(s), sum(s)) for tid, s in per_task.items()]
    summary = {
        "model": settings.model, "runs_per_task": runs,
        **aggregate_passk(aggs, max_k=runs),
        "compliance": compliance_metrics(records),
        "taxonomy": tax_aggregate(records)["counts"],
        "usage_total": usage.snapshot(),
    }
    _write_report(summary, per_task, records)
    return summary


def _write_report(summary: dict, per_task: dict, records: list[dict]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    passk = " | ".join(f"{k}={summary[k]}" for k in summary if k.startswith("pass^"))
    c = summary["compliance"]
    by_task = {tid: f"{sum(s)}/{len(s)}" for tid, s in per_task.items()}
    L = [
        "# Baseline Report — L1 single agent (M3 metrics)", "",
        f"- model: `{summary['model']}`  |  runs/task: {summary['runs_per_task']}  |  "
        f"tasks: {summary['n_tasks']}",
        f"- **pass@1 = {summary['pass@1']}** CI95 {summary['pass@1_ci95']}"
        + (f"  |  {passk}" if passk else ""),
        f"- policy_violation_rate = **{c['policy_violation_rate']}**  |  "
        f"unnecessary_handoff_rate = {c['unnecessary_handoff_rate']}  |  "
        f"escalation_precision = {c['human_escalation_precision']}",
        f"- avg_turns = {c['avg_turns_to_resolution']}  |  p95_latency = {c['latency_p95_s']}s  |  "
        f"cost/task = ${c['cost_per_task_usd']}",
        f"- error taxonomy: {summary['taxonomy'] or 'no failures'}",
        f"- total usage: {summary['usage_total']}", "",
        "## Per-task success (successes/runs)", "",
        "| " + " | ".join(by_task) + " |",
        "|" + "---|" * len(by_task),
        "| " + " | ".join(by_task.values()) + " |", "",
        "> pass@1 is a single/low-run estimate; run more (`python -m eval.runner 5`) for pass^k "
        "consistency. Statistical noise is real at this task count — CIs are reported.", "",
    ]
    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = run(runs=runs)
    print(json.dumps(out, indent=2))
    print(f"\n📄 report: {REPORT}")
