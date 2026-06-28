# Error Taxonomy

Trace-level failure labeling for after-sales agent runs. A rule-based classifier
(`eval/error_taxonomy.py`) labels each failed run; an LLM-as-judge
(`eval/judge.py`) screens ambiguous cases, with human spot-checking for calibration
(project definition v1 §9). A successful run gets no label.

## Classes

| class | meaning |
|---|---|
| `policy_violation` | a forbidden write executed (e.g. auto-refunded a high-value/ineligible item) |
| `premature_escalation` | escalated when not warranted (over-handoff on a trivial request) |
| `missing_param_no_clarify` | should have escalated/clarified but acted or failed instead |
| `tool_selection_error` | expected tool never called / wrong tool chosen |
| `intent_routing_error` | handled as the wrong intent |
| `tool_order_error` | right tools, wrong order (e.g. write before eligibility check) |
| `answer_tool_inconsistency` | final reply contradicts tool results |
| `long_context_forgetting` | lost earlier-confirmed information across turns |

## Live counts

Per-config taxonomy counts are emitted on every eval run — see the
**"Error taxonomy by config"** section of [`ablation_report.md`](ablation_report.md)
and the `error taxonomy:` line of [`baseline_report.md`](baseline_report.md) for the
current numbers (they change each run, so they are not duplicated here).

**Reading:** failures are dominated by `tool_selection_error` — the agent answering
without first calling `check_return_eligibility`, or skipping a required lookup.
`policy_violation` is consistently **0** across configs: on `deepseek-v4-flash` with
explicit policy the agent does not over-reach on writes, so the guardrail layer's value
is **defense-in-depth** (a code-enforced net for the cases the model gets wrong — proven
by the model-free regression gate and the security tests) rather than something this
small subset can separate by violation count.

> Regenerate counts from any run via `eval.error_taxonomy.aggregate(records)`.
