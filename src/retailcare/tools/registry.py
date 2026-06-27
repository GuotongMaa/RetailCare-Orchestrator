"""Tool registry: exposes the 8 tools to the LLM as OpenAI-style function specs,
and dispatches a tool call (name + json args) to the typed implementation.

This is the single source of truth the agent uses; the MCP server reuses it too.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from retailcare.tools import impl
from retailcare.tools.schema import (
    CheckReturnEligibilityIn,
    CreateReturnRequestIn,
    EscalateToHumanIn,
    GetCouponIn,
    GetOrderIn,
    GetShipmentIn,
    IssueCompensationIn,
    SearchPolicyIn,
)

# Fields the *system* injects at the trust boundary — the model never sees nor
# supplies them (user_id: session identity / D2; idempotency_key: derived / D3).
SERVER_INJECTED = {"user_id", "idempotency_key"}


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable
    writes: bool          # high-risk state-changing operation?
    requires_hitl: bool = False  # needs human-in-the-loop confirm/guardrail gating?

    def openai_spec(self) -> dict:
        schema = self.input_model.model_json_schema()
        schema.pop("title", None)
        # Strip server-injected fields so the model cannot express identity/idempotency.
        props = schema.get("properties", {})
        for f in SERVER_INJECTED:
            props.pop(f, None)
        if "required" in schema:
            schema["required"] = [r for r in schema["required"] if r not in SERVER_INJECTED]
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


REGISTRY: dict[str, ToolDef] = {
    t.name: t
    for t in [
        ToolDef("get_order", "Fetch the current customer's order and items by order_id.",
                GetOrderIn, impl.get_order, False),
        ToolDef("get_shipment", "Fetch shipment/tracking status for the customer's order.",
                GetShipmentIn, impl.get_shipment, False),
        ToolDef("search_policy", "Search the after-sales policy; returns versioned chunks.",
                SearchPolicyIn, impl.search_policy, False),
        ToolDef("get_coupon", "List the current customer's coupons.",
                GetCouponIn, impl.get_coupon, False),
        ToolDef("check_return_eligibility",
                "Check whether the customer's item can be returned/refunded; returns "
                "refund_amount and whether human review is required.",
                CheckReturnEligibilityIn, impl.check_return_eligibility, False),
        ToolDef("create_return_request",
                "WRITE: create a return/refund ticket for the customer's order. "
                "Idempotent on (order_id,item_id).",
                CreateReturnRequestIn, impl.create_return_request, True, requires_hitl=True),
        ToolDef("issue_compensation",
                "WRITE: issue goodwill compensation to the customer.",
                IssueCompensationIn, impl.issue_compensation, True, requires_hitl=True),
        ToolDef("escalate_to_human",
                "Hand off the conversation to a human agent with a reason and transcript.",
                EscalateToHumanIn, impl.escalate_to_human, True, requires_hitl=False),
    ]
}

# Single source of truth for which tools the guardrail/HITL layer gates (D6).
GATED_TOOLS = frozenset(name for name, t in REGISTRY.items() if t.requires_hitl)


def openai_tools() -> list[dict]:
    return [t.openai_spec() for t in REGISTRY.values()]


def dispatch(name: str, args: dict):
    """Validate args against the contract and call the implementation.

    Returns (result_jsonable, error_str). Exactly one is non-None.
    """
    tool = REGISTRY.get(name)
    if tool is None:
        return None, f"unknown tool: {name}"
    try:
        parsed = tool.input_model(**(args or {}))
    except Exception as e:  # validation error -> surfaced to the model
        return None, f"invalid arguments for {name}: {e}"
    try:
        result = tool.fn(parsed)
    except impl.ToolError as e:
        return None, str(e)
    return _jsonable(result), None


def _jsonable(obj):
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_jsonable(x) for x in obj]
    return obj
