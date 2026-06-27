"""Injectable clock — the single source of "now" for time-dependent policy
(return windows, expiry). Resolves in priority order:

1. an explicit override set via `set_now()` — used by the mock world: `seed()`
   pins "now" to the seed epoch so eligibility is deterministic for tests/eval;
2. the `RETAILCARE_NOW` env var (ISO-8601) — for reproducible runs/demos;
3. real wall-clock `datetime.utcnow()` — production against real data.

This replaces the old `from retailcare.data.seed import NOW` hard dependency, which
froze time even in production (docs/state-and-security-upgrade.md D12).
"""
from __future__ import annotations

import os
from datetime import datetime

_override: datetime | None = None


def set_now(dt: datetime | None) -> None:
    """Pin the clock (mock world). Pass None to clear back to env/wall-clock."""
    global _override
    _override = dt


def now() -> datetime:
    if _override is not None:
        return _override
    env = os.getenv("RETAILCARE_NOW")
    if env:
        try:
            return datetime.fromisoformat(env)
        except ValueError:
            pass
    return datetime.utcnow()
