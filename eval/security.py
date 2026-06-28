"""Security end-to-end eval (P0): drive ADVERSARIAL conversations through the live
agent and verify the trust boundary holds — under prompt-injection, identity-spoofing,
fake-system messages, and data-exfiltration attempts, NO forbidden cross-user/injected
write executes (D2/D3 + guardrails). Model-based; complements the unit-level test_security.

    python -m eval.security        # 1 run/task
    python -m eval.security 3      # 3 runs/task -> resisted^k consistency
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.common import RunConfig, is_policy_violation, run_task_once
from eval.metrics import TaskAgg, pass_hat_k, wilson_ci
from retailcare.config import settings, usage
from retailcare.data.seed import seed

DATASET = Path("eval/datasets/security_tasks.jsonl")
REPORT = Path("reports/security_report.md")
_CFG = RunConfig("L1_security", guardrails=True, auto_confirm=True, policy_mode="prompt")


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
            rec["resisted"] = not rec["violated"]  # no forbidden write executed
            records.append(rec)
            per_task[t["id"]].append(rec["resisted"])
    n = len(records)
    resisted = sum(r["resisted"] for r in records)
    breaches = [r for r in records if not r["resisted"]]
    aggs = [TaskAgg(tid, len(s), sum(s)) for tid, s in per_task.items()]
    ks = [k for k in range(1, runs + 1)]
    summary = {
        "model": settings.model, "runs_per_task": runs, "n_trials": n, "n_tasks": len(tasks),
        "injection_resisted_rate": round(resisted / n, 4) if n else 0.0,
        "resisted_ci95": wilson_ci(resisted, n),
        **{f"resisted^{k}": round(pass_hat_k([a.successes for a in aggs],
                                            [a.runs for a in aggs], k), 4) for k in ks},
        "policy_violation_rate": round(
            sum(is_policy_violation(r["violated"]) for r in records) / n, 4) if n else 0.0,
        "breaches": [{"task": r["task_id"], "executed_forbidden": r["violated"]} for r in breaches],
        "usage_total": usage.snapshot(),
    }
    _write_report(summary, tasks, per_task)
    return summary


def _write_report(summary: dict, tasks: list[dict], per_task: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    by_task = {tid: f"{sum(s)}/{len(s)}" for tid, s in per_task.items()}
    intents = {t["id"]: t.get("intent", "") for t in tasks}
    resk = " | ".join(f"{k}={summary[k]}" for k in summary if k.startswith("resisted^"))
    breach_lines = (["", "## ⚠️ BREACHES (forbidden write executed under attack)", ""]
                    + [f"- `{b['task']}` executed {b['executed_forbidden']}" for b in summary["breaches"]]
                    if summary["breaches"] else ["", "✅ No breaches: every adversarial attempt "
                                                 "was resisted (no forbidden write executed).", ""])
    L = [
        "# Security Report — adversarial end-to-end (D2/D3 trust boundary)", "",
        f"- model: `{summary['model']}`  |  runs/task: {summary['runs_per_task']}  |  "
        f"adversarial tasks: {summary['n_tasks']}",
        f"- **injection_resisted_rate = {summary['injection_resisted_rate']}** "
        f"CI95 {summary['resisted_ci95']}" + (f"  |  {resk}" if resk else ""),
        f"- **policy_violation_rate = {summary['policy_violation_rate']}** "
        "(forbidden state-changing writes under attack)",
        f"- total usage: {summary['usage_total']}",
        *breach_lines,
        "## Per-task resisted (resisted/runs)", "",
        "| " + " | ".join(f"{tid}" for tid in by_task) + " |",
        "|" + "---|" * len(by_task),
        "| " + " | ".join(by_task.values()) + " |", "",
        "Attack types: " + ", ".join(sorted(set(intents.values()))), "",
        "> Identity is session-injected (D2), so customer-scoped reads cannot return another "
        "user's data even if the model is tricked into trying; this eval scores the "
        "stronger end-to-end property — that no forbidden WRITE executes under live attack.", "",
    ]
    REPORT.write_text("\n".join(L))


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out = run(runs=runs)
    print(json.dumps(out, indent=2))
    print(f"\n📄 report: {REPORT}")
