"""Evaluation metrics: pass^k (consistency), confidence intervals, and the
task/tool/compliance metric family (project definition v1 §9).

pass^k uses the tau-bench unbiased estimator: for a task observed with c successes
out of n runs, the probability that k randomly drawn runs are ALL successes is
C(c,k)/C(n,k); we average this over tasks. pass^1 == mean success rate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def _comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def pass_hat_k(successes: list[int], runs: list[int], k: int) -> float:
    """successes[i]/runs[i] are per-task success counts. Returns averaged pass^k."""
    vals = []
    for c, n in zip(successes, runs, strict=True):
        if n < k:
            continue
        vals.append(_comb(c, k) / _comb(n, k))
    return sum(vals) / len(vals) if vals else 0.0


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (good for small n)."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    half = (z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))) / denom
    return (round(max(0.0, center - half), 4), round(min(1.0, center + half), 4))


@dataclass
class TaskAgg:
    task_id: str
    runs: int
    successes: int

    @property
    def rate(self) -> float:
        return self.successes / self.runs if self.runs else 0.0


def aggregate_passk(task_aggs: list[TaskAgg], max_k: int = 8) -> dict:
    succ = [t.successes for t in task_aggs]
    runs = [t.runs for t in task_aggs]
    min_runs = min(runs) if runs else 0
    ks = [k for k in range(1, max_k + 1) if k <= min_runs]
    out = {f"pass^{k}": round(pass_hat_k(succ, runs, k), 4) for k in ks}
    # overall pass@1 CI across all (task,run) trials
    total_succ = sum(succ)
    total = sum(runs)
    out["pass@1"] = round(total_succ / total, 4) if total else 0.0
    out["pass@1_ci95"] = wilson_ci(total_succ, total)
    out["n_tasks"] = len(task_aggs)
    out["runs_per_task"] = min_runs
    return out


def compliance_metrics(records: list[dict]) -> dict:
    """records: one per task-run with booleans/values. Keys used:
    policy_violation, unnecessary_handoff, escalation_correct, escalation_predicted,
    turns, latency_s, cost_usd."""
    n = len(records) or 1
    viol = sum(r.get("policy_violation", False) for r in records)
    unh = sum(r.get("unnecessary_handoff", False) for r in records)
    esc_pred = [r for r in records if r.get("escalation_predicted")]
    esc_ok = sum(r.get("escalation_correct", False) for r in esc_pred)
    latencies = sorted(r.get("latency_s", 0.0) for r in records)
    p95 = latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))] if latencies else 0.0
    return {
        "policy_violation_rate": round(viol / n, 4),
        "unnecessary_handoff_rate": round(unh / n, 4),
        "human_escalation_precision": round(esc_ok / len(esc_pred), 4) if esc_pred else None,
        "avg_turns_to_resolution": round(sum(r.get("turns", 0) for r in records) / n, 3),
        "latency_p95_s": round(p95, 3),
        "cost_per_task_usd": round(sum(r.get("cost_usd", 0.0) for r in records) / n, 6),
    }
