"""pass^k estimator + CI (deterministic)."""
from eval.common import is_policy_violation
from eval.metrics import TaskAgg, aggregate_passk, compliance_metrics, pass_hat_k, wilson_ci


def test_pass_hat_k_extremes():
    assert pass_hat_k([3], [3], 3) == 1.0          # always succeeds
    assert pass_hat_k([0], [3], 1) == 0.0          # never succeeds
    assert pass_hat_k([1], [2], 1) == 0.5          # 1 of 2
    assert pass_hat_k([1], [3], 3) == 0.0          # can't have 3 successes from 1


def test_pass_hat_k_consistency_drops_with_k():
    succ, runs = [3, 1], [3, 3]  # one reliable task, one flaky (1/3)
    p1 = pass_hat_k(succ, runs, 1)
    p3 = pass_hat_k(succ, runs, 3)
    assert p1 > p3                                  # consistency is harder
    assert abs(p1 - (1.0 + 1 / 3) / 2) < 1e-9       # avg of per-task rates
    assert abs(p3 - (1.0 + 0.0) / 2) < 1e-9


def test_aggregate_passk_keys():
    aggs = [TaskAgg("T1", 3, 3), TaskAgg("T2", 3, 1)]
    out = aggregate_passk(aggs, max_k=3)
    assert out["pass^1"] == round((3 + 1) / 6, 4)
    assert out["pass^3"] == 0.5
    assert out["runs_per_task"] == 3
    assert isinstance(out["pass@1_ci95"], tuple)


def test_wilson_ci_bounds():
    lo, hi = wilson_ci(8, 10)
    assert 0.0 <= lo < 0.8 < hi <= 1.0


def test_compliance_metrics():
    recs = [
        {"policy_violation": False, "escalation_predicted": True, "escalation_correct": True,
         "turns": 2, "latency_s": 1.0, "cost_usd": 0.001},
        {"policy_violation": True, "unnecessary_handoff": True, "turns": 4,
         "latency_s": 3.0, "cost_usd": 0.002},
    ]
    m = compliance_metrics(recs)
    assert m["policy_violation_rate"] == 0.5
    assert m["unnecessary_handoff_rate"] == 0.5
    assert m["human_escalation_precision"] == 1.0


def test_policy_violation_scope_excludes_premature_escalation():
    assert is_policy_violation(["create_return_request"]) is True
    assert is_policy_violation(["issue_compensation"]) is True
    assert is_policy_violation(["escalate_to_human"]) is False
