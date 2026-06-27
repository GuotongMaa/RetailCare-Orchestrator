# RetailCare Learning Lab

This folder is the isolated sandbox for learning code.

Use it for:

- small scripts that inspect RetailCare behavior;
- prototypes for new tools, prompts, eval cases, or UI ideas;
- notebooks or throwaway experiments;
- module-specific exercises.

Do not use it for:

- production agent runtime code;
- code imported by `src/retailcare`;
- tests that the main project depends on;
- permanent business rules.

## Structure

```text
learning_lab/
  modules/      # module-by-module exercises
  experiments/  # prototypes that may or may not be promoted
```

Suggested module folders:

```text
learning_lab/modules/module_01_python_foundations/
learning_lab/modules/module_02_agent_framework/
learning_lab/modules/module_03_tool_calling/
```

## Import Rule

Learning code may import from the main project:

```python
from retailcare.data.seed import seed
from retailcare.tools.registry import dispatch
```

Main project code must never import from `learning_lab`.

## Promotion

If an experiment becomes valuable, follow
`docs/learning/promotion-policy.md` before moving it into `src/`, `eval/`,
`tests/`, or `web/`.
