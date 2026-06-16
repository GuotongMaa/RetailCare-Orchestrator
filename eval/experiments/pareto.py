"""E6 — quality x cost Pareto (project definition v1 §10 E6).

Runs the same task subset under each available model (DeepSeek v4 flash vs pro) and
plots quality (pass@1) against cost ($/task) as an ASCII Pareto, the 2026
'cost-aware eval' angle. Pro is the strong model, flash the cheap one.

    python -m eval.experiments.pareto [R] [subset_size]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.common import RunConfig, run_task_once
from eval.metrics import TaskAgg, aggregate_passk, compliance_metrics
from eval.runner import load_tasks
from retailcare.config import settings
from retailcare.data.seed import seed

REPORT = Path("reports/pareto_report.md")
SUBSET_IDS = ["T01", "T04", "T06", "T07", "T09", "T12", "T14", "T16", "T26", "T31"]


def _run_model(model: str, tasks: list[dict], runs: int) -> dict:
    records, per_task = [], {t["id"]: [] for t in tasks}
    cfg = RunConfig(f"eval-{model}", guardrails=True, auto_confirm=True, model=model)
    for _ in range(runs):
        seed(reset=True)
        for t in tasks:
            rec = run_task_once(t, cfg)
            per_task[t["id"]].append(rec["success"])
            records.append(rec)
    aggs = [TaskAgg(tid, len(s), sum(s)) for tid, s in per_task.items()]
    pk = aggregate_passk(aggs, max_k=runs)
    cm = compliance_metrics(records)
    return {"model": model, "pass@1": pk["pass@1"], "ci95": pk["pass@1_ci95"],
            "cost_per_task": cm["cost_per_task_usd"], "p95": cm["latency_p95_s"],
            "violation_rate": cm["policy_violation_rate"]}


def run(runs: int = 2, subset_size: int | None = None) -> list[dict]:
    all_tasks = {t["id"]: t for t in load_tasks()}
    ids = SUBSET_IDS[:subset_size] if subset_size else SUBSET_IDS
    tasks = [all_tasks[i] for i in ids if i in all_tasks]
    models = sorted({settings.model_weak, settings.model_strong})
    results = [_run_model(m, tasks, runs) for m in models]
    _write_report(results, tasks, runs)
    return results


def _write_report(results: list[dict], tasks: list[dict], runs: int) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    maxc = max((r["cost_per_task"] for r in results), default=1e-6) or 1e-6
    L = ["# Quality x Cost Pareto (E6)", "",
         f"- subset: {len(tasks)} tasks  |  runs/task: {runs}", "",
         "| model | pass@1 (CI95) | cost/task | p95 | violations |",
         "|---|---|---|---|---|"]
    for r in sorted(results, key=lambda x: x["cost_per_task"]):
        L.append(f"| `{r['model']}` | {r['pass@1']} {r['ci95']} | ${r['cost_per_task']} | "
                 f"{r['p95']}s | {r['violation_rate']} |")
    L += ["", "## Pareto (quality vs cost)", "```"]
    for r in sorted(results, key=lambda x: x["cost_per_task"]):
        bar = "█" * max(1, int(40 * r["cost_per_task"] / maxc))
        L.append(f"{r['model']:>18}  q={r['pass@1']:.3f}  ${r['cost_per_task']:.5f}  {bar}")
    L += ["```", "",
          "> Cost-aware evaluation (2026): route low-risk reads to the cheap model, keep the "
          "strong model for high-risk refund reasoning, and pick the point on this frontier.",
          ">", "> Caveat: `$/task` uses a single placeholder price for both models "
          "(`RETAILCARE_PRICE_*`), so it reflects token volume, not true per-model pricing. "
          "Plug real DeepSeek prices for a dollar frontier; quality and token counts are direct.",
          ""]
    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    subset = int(sys.argv[2]) if len(sys.argv) > 2 else None
    out = run(runs=runs, subset_size=subset)
    print(json.dumps(out, indent=2))
    print(f"\n📄 report: {REPORT}")
