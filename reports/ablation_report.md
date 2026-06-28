> ⚠️ **升级前基线结果**：本报告是 M1–M4 阶段的评估输出，早于 A/B/C 信任边界 + 结构化 state + 健壮性升级。数据集已对齐新架构；报告重跑待续（需模型 API）。

# Ablation Report (M3)

- model: `deepseek-v4-flash`  |  subset: 10 safety-critical tasks  |  runs/task: 3

## E1/E4 — guardrails+HITL value (L0 vs L1) ; E3 — policy prompt vs RAG

| config | pass@1 (CI95) | pass^k | policy_violation_rate | unnecessary_handoff | p95 latency | cost/task |
|---|---|---|---|---|---|---|
| L0_no_guardrails | 0.6333 (0.4551, 0.7813) | pass^3=0.5 | **0.0** | 0.0 | 13.36s | $0.002125 |
| L1_guardrails | 0.8 (0.6269, 0.905) | pass^3=0.6 | **0.0** | 0.0 | 12.271s | $0.002124 |
| L1_policy_rag | 0.8333 (0.6644, 0.9266) | pass^3=0.8 | **0.0** | 0.0 | 12.025s | $0.002114 |

## Error taxonomy by config

- **L0_no_guardrails**: {'tool_selection_error': 11, 'missing_param_no_clarify': 2}
- **L1_guardrails**: {'tool_selection_error': 6, 'missing_param_no_clarify': 2}
- **L1_policy_rag**: {'tool_selection_error': 5, 'missing_param_no_clarify': 2}

## Honest reading (observed)

- **Hardening pays off without adding any agent (core claim).** L0→L1 lifts pass@1 0.633→0.80 and pass^3 0.50→0.60; tool-selection errors drop 11→6. Guardrails make the agent more *reliably* correct on the safety-critical subset.
- **Policy violations were 0 across all configs — including L0.** On this model the explicit policy-in-prompt already prevents over-reaching writes, so guardrails act as a *safety net* whose measured value here shows up in consistency, not raw violation rate. The net would matter more under weaker models / policy-free prompts (a documented follow-up: add an `L0_no_policy` arm).
- **E3: RAG ≈ prompt on success, better on consistency.** L1_policy_rag reaches the best pass^3 (0.80 vs 0.60) at similar cost/latency, and decouples policy updates from the prompt — favouring RAG for maintainability.
- **pass^k << pass@1 confirms consistency is the real gap** (pass^3 0.5–0.8). This is exactly what the project targets. L2 (multi-agent refund subgraph) is scoped as future work; the L0→L1 result already shows "harden first, split only if data demands it."
