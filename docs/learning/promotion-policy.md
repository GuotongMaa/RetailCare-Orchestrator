# Promotion Policy

Use this policy when deciding whether learning code should become part of the
main RetailCare architecture.

## Default Rule

Learning code starts in `learning_lab/`. It stays there unless there is a clear
reason to promote it.

The main architecture includes:

- `src/retailcare/`
- `eval/`
- `tests/`
- `web/`
- root operational docs such as `README.md`, `ARCHITECTURE.md`, and
  `OPERATIONS_MANUAL.md`

## Allowed Direction

Allowed:

```text
learning_lab -> imports/observes -> src/retailcare
```

Not allowed:

```text
src/retailcare -> imports -> learning_lab
eval/tests/web -> depends on -> learning_lab
```

## Promotion Checklist

Before moving a learning experiment into the main architecture, answer:

- What user, business, reliability, or learning value does this add?
- Which module boundary does it belong to?
- What existing behavior could it change?
- What test, eval, or trace proves it works?
- Does it preserve idempotency, policy compliance, and safe failure behavior?
- Can it be rolled back cleanly?

## Promotion Paths

Tool experiment:

```text
learning_lab/experiments/tool_x
  -> src/retailcare/tools/schema.py
  -> src/retailcare/tools/impl.py
  -> src/retailcare/tools/registry.py
  -> src/retailcare/mcp_server/server.py
  -> tests/test_tools.py
  -> optional eval case
```

Eval experiment:

```text
learning_lab/experiments/eval_case_x
  -> eval/datasets/*.jsonl
  -> eval/regression.py or eval/runner.py
  -> tests/test_metrics.py if metric logic changes
```

UI experiment:

```text
learning_lab/experiments/ui_x
  -> web/index.html
  -> manual browser check
```

## Session Note Requirement

When promoting anything, update:

- `docs/learning/progress.md`
- the relevant `docs/learning/sessions/*.md`
- `docs/learning/decisions.md` if the change affects architecture or learning
  process
