# Quality x Cost Pareto (E6)

- subset: 10 tasks  |  runs/task: 2

| model | pass@1 (CI95) | cost/task | p95 | violations |
|---|---|---|---|---|
| `deepseek-v4-pro` | 0.85 (0.6396, 0.9476) | $0.001912 | 19.663s | 0.0 |
| `deepseek-v4-flash` | 0.95 (0.7639, 0.9911) | $0.002188 | 12.257s | 0.0 |

## Pareto (quality vs cost)
```
   deepseek-v4-pro  q=0.850  $0.00191  ██████████████████████████████████
 deepseek-v4-flash  q=0.950  $0.00219  ████████████████████████████████████████
```

> Cost-aware evaluation (2026): route low-risk reads to the cheap model, keep the strong model for high-risk refund reasoning, and pick the point on this frontier.
>
> Caveat: `$/task` uses a single placeholder price for both models (`RETAILCARE_PRICE_*`), so it reflects token volume, not true per-model pricing. Plug real DeepSeek prices for a dollar frontier; quality and token counts are direct.
