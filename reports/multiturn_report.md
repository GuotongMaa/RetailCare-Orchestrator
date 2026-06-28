# Multi-turn / Business-switch Report (state grounding, B)

- model: `deepseek-v4-flash`  |  runs/task: 2  |  tasks: 6
- **pass@1 = 0.9167** CI95 (0.6461, 0.9851)  |  pass^1=0.9167 | pass^2=0.8333
- state-grounding failures (acted on wrong order after a switch): ['M06']
- total usage: {'calls': 69, 'prompt_tokens': 136840, 'completion_tokens': 9901, 'cost_usd': 0.042474}

| task | intent | turns | per-turn | success |
|---|---|---|---|---|
| M01 | switch_shipping_to_return_same_order | 2 | ✅✅ | 2/2 |
| M02 | cross_order_switch | 2 | ✅✅ | 2/2 |
| M03 | coupons_then_order | 2 | ✅✅ | 2/2 |
| M04 | clarify_then_act | 2 | ✅✅ | 2/2 |
| M05 | switch_away_and_back | 3 | ✅✅✅ | 2/2 |
| M06 | status_then_highvalue_escalate | 2 | ✅❌ | 1/2 |

> A task passes only if EVERY turn calls the required tools, avoids forbidden ones, and targets the expected order — so a business switch (or switch-back) that loses the focus order fails the task. Exercises the digest/focus-stack (D1/D8).
