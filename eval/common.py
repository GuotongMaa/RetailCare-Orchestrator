"""Shared per-run evaluation: run one task under a config, return an outcome record
(success + action-level compliance + cost/latency/turns). Reused by the baseline
runner and the ablation experiments.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from retailcare.config import usage
from retailcare.graph.runtime import Conversation


@dataclass
class RunConfig:
    name: str
    guardrails: bool = True
    auto_confirm: bool = True
    policy_mode: str = "prompt"  # "prompt" | "rag"


def executed_tools(conv: Conversation) -> list[str]:
    return [e.name for e in conv.trace.events if e.kind == "tool_call"]


def run_task_once(task: dict, cfg: RunConfig) -> dict:
    conv = Conversation(user_id=task["user_id"], auto_confirm=cfg.auto_confirm,
                        guardrails=cfg.guardrails, policy_mode=cfg.policy_mode)
    before = usage.snapshot()
    t0 = time.time()
    error = None
    try:
        conv.send(task["message"])
    except Exception as e:  # noqa: BLE001
        error = repr(e)
    latency = time.time() - t0
    after = usage.snapshot()

    called = executed_tools(conv)
    called_set = set(called)
    expected = set(task.get("expected_actions", []))
    forbidden = set(task.get("forbidden_actions", []))
    missing = expected - called_set
    violated = forbidden & called_set
    success = not error and not missing and not violated

    esc_pred = "escalate_to_human" in called_set
    esc_expected = "escalate_to_human" in expected
    return {
        "task_id": task["id"], "intent": task.get("intent"), "success": success,
        "missing": sorted(missing), "violated": sorted(violated), "error": error,
        "called": called,
        # compliance signals
        "policy_violation": bool(violated),
        "escalation_predicted": esc_pred,
        "escalation_correct": esc_pred and esc_expected,
        "unnecessary_handoff": esc_pred and "escalate_to_human" in forbidden,
        "turns": sum(1 for e in conv.trace.events if e.kind == "tool_call"),
        "latency_s": latency,
        "cost_usd": after["cost_usd"] - before["cost_usd"],
        "trace_session": conv.trace.session_id,
    }
