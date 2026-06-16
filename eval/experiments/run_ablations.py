"""Ablation experiments (project definition v1 §10).

E1/E4 — does hardening with guardrails+HITL help?  L0 (no guardrails, direct
        execution) vs L1 (guardrails + confirm/escalate). Main metrics: pass^k,
        policy_violation_rate.
E3    — how should policy enter?  policy-in-prompt vs RAG-retrieved. Metric:
        pass^k + violations + cost.

Runs a focused subset (the safety-critical refund tasks) R times per config.

    python -m eval.experiments.run_ablations [R] [subset_size]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.common import RunConfig, run_task_once
from eval.error_taxonomy import aggregate as tax_aggregate
from eval.metrics import TaskAgg, aggregate_passk, compliance_metrics
from eval.runner import load_tasks
from retailcare.config import settings
from retailcare.data.seed import seed

REPORT = Path("reports/ablation_report.md")

# Safety-critical subset where guardrails should matter most.
SUBSET_IDS = ["T01", "T02", "T03", "T04", "T05", "T12", "T14", "T15", "T16", "T26"]

CONFIGS = [
    RunConfig("L0_no_guardrails", guardrails=False, policy_mode="prompt"),
    RunConfig("L1_guardrails", guardrails=True, policy_mode="prompt"),
    RunConfig("L1_policy_rag", guardrails=True, policy_mode="rag"),
]


def _run_config(cfg: RunConfig, tasks: list[dict], runs: int) -> dict:
    records: list[dict] = []
    per_task: dict[str, list[bool]] = {t["id"]: [] for t in tasks}
    for _ in range(runs):
        seed(reset=True)  # fresh DB each run so writes don't dedup across runs
        for t in tasks:
            rec = run_task_once(t, cfg)
            records.append(rec)
            per_task[t["id"]].append(rec["success"])
    aggs = [TaskAgg(tid, len(s), sum(s)) for tid, s in per_task.items()]
    return {
        "config": cfg.name,
        "passk": aggregate_passk(aggs, max_k=runs),
        "compliance": compliance_metrics(records),
        "taxonomy": tax_aggregate(records),
    }


def run(runs: int = 3, subset_size: int | None = None) -> list[dict]:
    all_tasks = {t["id"]: t for t in load_tasks()}
    ids = SUBSET_IDS[:subset_size] if subset_size else SUBSET_IDS
    tasks = [all_tasks[i] for i in ids if i in all_tasks]
    results = [_run_config(c, tasks, runs) for c in CONFIGS]
    _write_report(results, tasks, runs)
    return results


def _write_report(results: list[dict], tasks: list[dict], runs: int) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    L = [
        "# Ablation Report (M3)", "",
        f"- model: `{settings.model}`  |  subset: {len(tasks)} safety-critical tasks  "
        f"|  runs/task: {runs}", "",
        "## E1/E4 — guardrails+HITL value (L0 vs L1) ; E3 — policy prompt vs RAG", "",
        "| config | pass@1 (CI95) | pass^k | policy_violation_rate | unnecessary_handoff "
        "| p95 latency | cost/task |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        pk = r["passk"]
        kmax = max((int(k.split("^")[1]) for k in pk if k.startswith("pass^")), default=1)
        c = r["compliance"]
        L.append(
            f"| {r['config']} | {pk.get('pass@1')} {pk.get('pass@1_ci95')} | "
            f"pass^{kmax}={pk.get(f'pass^{kmax}')} | **{c['policy_violation_rate']}** | "
            f"{c['unnecessary_handoff_rate']} | {c['latency_p95_s']}s | ${c['cost_per_task_usd']} |")
    L += ["", "## Error taxonomy by config", ""]
    for r in results:
        L.append(f"- **{r['config']}**: {r['taxonomy']['counts'] or 'no failures'}")
    L += ["", "## Honest reading", "",
          "- If L1 policy_violation_rate < L0, hardening (guardrails+HITL) pays off without "
          "adding any agent — the project's core claim.",
          "- E3: compare prompt vs RAG on violations/cost; RAG decouples policy updates from "
          "the prompt at some latency/cost.",
          "- pass^k << pass@1 would reveal consistency gaps (the real target). L2 (multi-agent "
          "refund subgraph) is scoped as future work.", ""]
    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    subset = int(sys.argv[2]) if len(sys.argv) > 2 else None
    out = run(runs=runs, subset_size=subset)
    print(json.dumps([{"config": r["config"], **r["passk"],
                       "violations": r["compliance"]["policy_violation_rate"]} for r in out],
                     indent=2))
    print(f"\n📄 report: {REPORT}")
