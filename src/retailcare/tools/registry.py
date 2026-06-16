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


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable
    writes: bool  # high-risk write operation?

    def openai_spec(self) -> dict:
        schema = self.input_model.model_json_schema()
        schema.pop("title", None)
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
        ToolDef("get_order", "Fetch an order and its items by order_id.",
                GetOrderIn, impl.get_order, False),
        ToolDef("get_shipment", "Fetch shipment/tracking status for an order_id.",
                GetShipmentIn, impl.get_shipment, False),
        ToolDef("search_policy", "Search the after-sales policy; returns versioned chunks.",
                SearchPolicyIn, impl.search_policy, False),
        ToolDef("get_coupon", "List a user's coupons by user_id.",
                GetCouponIn, impl.get_coupon, False),
        ToolDef("check_return_eligibility",
                "Check whether an item can be returned/refunded; returns refund_amount and "
                "whether human review is required.",
                CheckReturnEligibilityIn, impl.check_return_eligibility, False),
        ToolDef("create_return_request",
                "WRITE: create a return/refund ticket. Idempotent on (order_id,item_id). "
                "Requires idempotency_key.",
                CreateReturnRequestIn, impl.create_return_request, True),
        ToolDef("issue_compensation",
                "WRITE: issue goodwill compensation. Requires idempotency_key.",
                IssueCompensationIn, impl.issue_compensation, True),
        ToolDef("escalate_to_human",
                "Hand off the conversation to a human agent with a reason and transcript.",
                EscalateToHumanIn, impl.escalate_to_human, True),
    ]
}


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
