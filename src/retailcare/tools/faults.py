"""Fault injection for resilience testing (project definition v1 §6).

Off by default. Tests / the fault-injection eval enable specific faults so we can
prove the retry -> fallback -> escalate degradation path, which tau2/tau3 do not
cover (a differentiation point).
"""
from __future__ import annotations

from dataclasses import dataclass

TRANSIENT = {"timeout", "error"}


@dataclass
class FaultSpec:
    mode: str  # "timeout" | "error" | "stale"
    times: int  # number of times to trigger before succeeding (large = permanent)


_ACTIVE: dict[str, FaultSpec] = {}


def inject(tool: str, mode: str, times: int = 1) -> None:
    _ACTIVE[tool] = FaultSpec(mode=mode, times=times)


def clear() -> None:
    _ACTIVE.clear()


def check(tool: str) -> str | None:
    """Return the fault mode to apply for this call (and consume one), else None."""
    spec = _ACTIVE.get(tool)
    if not spec or spec.times <= 0:
        return None
    spec.times -= 1
    return spec.mode
