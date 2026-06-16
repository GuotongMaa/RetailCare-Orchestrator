"""Bounded retry + graceful degradation around tool dispatch (BUSINESS_RULES §5).

Transient faults (timeout/error) are retried up to MAX_RETRIES; if still failing,
we return a degraded signal so the agent escalates rather than acting on bad state.
'stale' data is passed through but flagged so downstream can decide.
"""
from __future__ import annotations

from retailcare.tools import faults
from retailcare.tools.registry import dispatch

MAX_RETRIES = 2


def call_with_recovery(name: str, args: dict, trace=None):
    """Returns (result_jsonable, error_str). On unrecoverable fault, error_str
    carries an escalation hint."""
    attempts = 0
    while True:
        mode = faults.check(name)
        if mode in faults.TRANSIENT:
            attempts += 1
            if trace:
                trace.tool_error(name, f"injected {mode}", attempt=attempts, recovered=False)
            if attempts <= MAX_RETRIES:
                continue
            msg = (f"{name} failed after {attempts} attempts ({mode}); "
                   f"degrade gracefully and escalate_to_human — do not act on uncertain state")
            if trace:
                trace.decision("recovery", "give_up", tool=name, attempts=attempts)
            return None, msg

        if attempts and trace:
            trace.decision("recovery", "recovered", tool=name, attempts=attempts)

        result, err = dispatch(name, args)
        if err:
            return None, err
        if mode == "stale" and isinstance(result, dict):
            return {"_stale": True, **result}, None
        return result, None
