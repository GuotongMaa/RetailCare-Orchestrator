# Baseline Report — L1 single agent (M3 metrics)

- model: `deepseek-v4-flash`  |  runs/task: 3  |  tasks: 35
- **pass@1 = 0.9714** CI95 (0.9193, 0.9902)  |  pass^1=0.9714 | pass^2=0.9524 | pass^3=0.9429
- policy_violation_rate = **0.0**  |  unnecessary_handoff_rate = 0.0  |  escalation_precision = 1.0
- avg_turns = 2.248  |  p95_latency = 13.115s  |  cost/task = $0.001816
- error taxonomy: {'eligibility_tool_omission': 3}
- total usage: {'calls': 316, 'prompt_tokens': 598730, 'completion_tokens': 54791, 'cost_usd': 0.190657}

## Per-task success (successes/runs)

| T01 | T02 | T03 | T04 | T05 | T06 | T07 | T08 | T09 | T10 | T11 | T12 | T13 | T14 | T15 | T16 | T17 | T18 | T19 | T20 | T21 | T22 | T23 | T24 | T25 | T26 | T27 | T28 | T29 | T30 | T31 | T32 | T33 | T34 | T35 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3/3 | 3/3 | 1/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 |

> pass@1 is a single/low-run estimate; run more (`python -m eval.runner 5`) for pass^k consistency. Statistical noise is real at this task count — CIs are reported.
