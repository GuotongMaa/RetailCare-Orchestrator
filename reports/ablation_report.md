# Ablation Report (M3)

- model: `deepseek-v4-flash`  |  subset: 3 safety-critical tasks  |  runs/task: 1

## E1/E4 — guardrails+HITL value (L0 vs L1) ; E3 — policy prompt vs RAG

| config | pass@1 (CI95) | pass^k | policy_violation_rate | unnecessary_handoff | p95 latency | cost/task |
|---|---|---|---|---|---|---|
| L0_no_guardrails | 1.0 (0.4385, 1.0) | pass^1=1.0 | **0.0** | 0.0 | 10.782s | $0.002018 |
| L1_guardrails | 0.6667 (0.2077, 0.9385) | pass^1=0.6667 | **0.0** | 0.0 | 9.458s | $0.001837 |
| L1_policy_rag | 0.6667 (0.2077, 0.9385) | pass^1=0.6667 | **0.0** | 0.0 | 10.799s | $0.00177 |

## Error taxonomy by config

- **L0_no_guardrails**: no failures
- **L1_guardrails**: {'tool_selection_error': 1}
- **L1_policy_rag**: {'tool_selection_error': 1}

## Honest reading

- If L1 policy_violation_rate < L0, hardening (guardrails+HITL) pays off without adding any agent — the project's core claim.
- E3: compare prompt vs RAG on violations/cost; RAG decouples policy updates from the prompt at some latency/cost.
- pass^k << pass@1 would reveal consistency gaps (the real target). L2 (multi-agent refund subgraph) is scoped as future work.
