# Ablation Report (M3)

- model: `deepseek-v4-flash`  |  subset: 10 safety-critical tasks  |  runs/task: 3

## E1/E4 — guardrails+HITL value (L0 vs L1) ; E3 — policy prompt vs RAG

| config | pass@1 (CI95) | pass^k | policy_violation_rate | unnecessary_handoff | p95 latency | cost/task |
|---|---|---|---|---|---|---|
| L0_no_guardrails | 0.7333 (0.5555, 0.8582) | pass^3=0.6 | **0.0** | 0.0 | 13.208s | $0.002238 |
| L1_guardrails | 0.7 (0.5212, 0.8334) | pass^3=0.5 | **0.0** | 0.0 | 12.112s | $0.002124 |
| L1_policy_rag | 0.7 (0.5212, 0.8334) | pass^3=0.6 | **0.0** | 0.0 | 14.536s | $0.00214 |

## Error taxonomy by config

- **L0_no_guardrails**: {'tool_selection_error': 8, 'missing_param_no_clarify': 1}
- **L1_guardrails**: {'tool_selection_error': 9, 'missing_param_no_clarify': 1}
- **L1_policy_rag**: {'tool_selection_error': 9, 'missing_param_no_clarify': 1}

## Honest reading

- If L1 policy_violation_rate < L0, hardening (guardrails+HITL) pays off without adding any agent — the project's core claim.
- E3: compare prompt vs RAG on violations/cost; RAG decouples policy updates from the prompt at some latency/cost.
- pass^k << pass@1 would reveal consistency gaps (the real target). L2 (multi-agent refund subgraph) is scoped as future work.
