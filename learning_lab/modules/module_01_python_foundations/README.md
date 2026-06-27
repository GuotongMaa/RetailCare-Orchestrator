# Module 01: Python + Async Foundations

This folder is for learning-only exercises related to Python project structure,
FastAPI, database access, command-line entrypoints, and local test execution.

It is intentionally separate from the main RetailCare architecture.

## Production Files To Inspect

- `pyproject.toml`
- `requirements.txt`
- `Makefile`
- `.env.example`
- `src/retailcare/config.py`
- `src/retailcare/api/app.py`
- `src/retailcare/cli.py`
- `src/retailcare/demo.py`
- `src/retailcare/data/db.py`
- `src/retailcare/data/models.py`
- `src/retailcare/data/seed.py`
- `tests/test_smoke.py`

## Safe Exercises

Learning scripts can be added here, for example:

- inspect seeded orders without changing production code;
- print database connection settings safely;
- call a read-only tool through the registry;
- trace how a FastAPI request maps to runtime code.

Do not import from this folder in `src/retailcare`.

## Baseline Check

Current baseline command:

```bash
make test
```

Current result observed on 2026-06-19:

```text
39 passed, 16 warnings
```

Warnings were dependency/runtime warnings from Python 3.14, SQLAlchemy datetime
defaults, and Chroma telemetry. They did not fail the test suite.
