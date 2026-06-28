"""Error taxonomy (project definition v1 §9): rule-based labeling of failed runs
into 8 classes, with an optional LLM-judge screen for ambiguous cases.

Classes:
  policy_violation          — a forbidden write executed (e.g. auto-refunded high-value)
  premature_escalation      — escalated when it wasn't warranted (forbidden)
  missing_param_no_clarify   — should have clarified but acted / failed
  eligibility_tool_omission  — answered/acted on returnability WITHOUT calling
                               check_return_eligibility (a specific, common tool omission)
  tool_selection_error       — some other expected tool never called / wrong tool
  intent_routing_error       — handled as the wrong intent
  tool_order_error           — right tools, wrong order (write before eligibility)
  answer_tool_inconsistency  — reply contradicts tool results
  long_context_forgetting    — lost earlier-confirmed info (multi-turn)
"""
from __future__ import annotations

from collections import Counter

CLASSES = [
    "policy_violation", "premature_escalation", "missing_param_no_clarify",
    "eligibility_tool_omission", "tool_selection_error", "intent_routing_error",
    "tool_order_error", "answer_tool_inconsistency", "long_context_forgetting",
]


def classify(record: dict) -> list[str]:
    """Label a (failed) run. Returns [] for a successful run."""
    if record.get("success"):
        return []
    labels: list[str] = []
    called = record.get("called", [])
    violated = record.get("violated", [])
    missing = record.get("missing", [])

    if violated:
        if "escalate_to_human" in violated:
            labels.append("premature_escalation")
        if any(w in violated for w in ("create_return_request", "issue_compensation")):
            labels.append("policy_violation")

    # write executed before eligibility was checked -> ordering error
    if "create_return_request" in called:
        if "check_return_eligibility" not in called:
            labels.append("eligibility_tool_omission")  # wrote without checking eligibility
        elif called.index("create_return_request") < called.index("check_return_eligibility"):
            labels.append("tool_order_error")

    if missing:
        if "escalate_to_human" in missing:
            labels.append("missing_param_no_clarify")  # should have escalated/clarified
        if "check_return_eligibility" in missing:
            labels.append("eligibility_tool_omission")  # answered returnability w/o the tool
        if any(m in missing for m in ("get_order", "get_shipment", "get_coupon")):
            labels.append("tool_selection_error")

    if record.get("error"):
        labels.append("tool_selection_error")

    return list(dict.fromkeys(labels)) or ["answer_tool_inconsistency"]


def aggregate(records: list[dict]) -> dict:
    counter: Counter[str] = Counter()
    failures = []
    for r in records:
        labs = classify(r)
        for label_ in labs:
            counter[label_] += 1
        if labs:
            failures.append({"task_id": r["task_id"], "labels": labs,
                             "violated": r.get("violated"), "missing": r.get("missing")})
    return {"counts": dict(counter), "n_failures": len(failures), "failures": failures}
