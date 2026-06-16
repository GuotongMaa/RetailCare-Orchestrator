# Quality x Cost Pareto (E6)

- subset: 10 tasks  |  runs/task: 2

| model | pass@1 (CI95) | cost/task | p95 | violations |
|---|---|---|---|---|
| `deepseek-v4-pro` | 0.95 (0.7639, 0.9911) | $0.001765 | 12.278s | 0.0 |
| `deepseek-v4-flash` | 0.95 (0.7639, 0.9911) | $0.002234 | 12.672s | 0.0 |

## Pareto (quality vs cost)
```
   deepseek-v4-pro  q=0.950  $0.00177  ███████████████████████████████
 deepseek-v4-flash  q=0.950  $0.00223  ████████████████████████████████████████
```

> Cost-aware evaluation (2026): route low-risk reads to the cheap model, keep the strong model for high-risk refund reasoning, and pick the point on this frontier.
>
> **Caveat (honest):** `$/task` uses a single placeholder price for both models
> (`RETAILCARE_PRICE_*` in `.env`), so it currently reflects **token volume**, not true
> per-model pricing — pro emits fewer tokens here, hence its lower number. Plug real
> per-model DeepSeek prices for a true dollar frontier. Quality (pass@1) and token counts
> are measured directly.
