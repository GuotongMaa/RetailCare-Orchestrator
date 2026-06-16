# Baseline Report — L1 single agent (M3 metrics)

- model: `deepseek-v4-flash`  |  runs/task: 3  |  tasks: 32
- **pass@1 = 0.9479** CI95 (0.8838, 0.9776)  |  pass^1=0.9479 | pass^2=0.9062 | pass^3=0.875
- policy_violation_rate = **0.0**  |  unnecessary_handoff_rate = 0.0  |  escalation_precision = 1.0
- avg_turns = 2.25  |  p95_latency = 12.05s  |  cost/task = $0.001747
- error taxonomy: {'tool_selection_error': 5, 'missing_param_no_clarify': 1}
- total usage: {'calls': 286, 'prompt_tokens': 521268, 'completion_tokens': 51889, 'cost_usd': 0.167748}

## Per-task success (successes/runs)

| T01 | T02 | T03 | T04 | T05 | T06 | T07 | T08 | T09 | T10 | T11 | T12 | T13 | T14 | T15 | T16 | T17 | T18 | T19 | T20 | T21 | T22 | T23 | T24 | T25 | T26 | T27 | T28 | T29 | T30 | T31 | T32 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3/3 | 3/3 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 | 3/3 | 2/3 | 3/3 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

> pass@1 is a single/low-run estimate; run more (`python -m eval.runner 5`) for pass^k consistency. Statistical noise is real at this task count — CIs are reported.
