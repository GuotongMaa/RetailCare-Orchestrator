"""MCP server exposing the after-sales tool layer (2026 standard tool contract).

Run as a stdio MCP server:   python -m retailcare.mcp_server.server
The same typed implementations back both the in-process agent and this server,
so tools are reusable by any MCP-capable client/IDE.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

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

mcp = FastMCP("retailcare-tools")


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Fetch an order and its items by order_id."""
    return impl.get_order(GetOrderIn(order_id=order_id)).model_dump(mode="json")


@mcp.tool()
def get_shipment(order_id: str) -> dict:
    """Fetch shipment/tracking status for an order_id."""
    return impl.get_shipment(GetShipmentIn(order_id=order_id)).model_dump(mode="json")


@mcp.tool()
def search_policy(query: str, k: int = 3) -> list[dict]:
    """Search the after-sales policy; returns versioned chunks."""
    return [c.model_dump(mode="json") for c in impl.search_policy(SearchPolicyIn(query=query, k=k))]


@mcp.tool()
def get_coupon(user_id: str) -> list[dict]:
    """List a user's coupons by user_id."""
    return [c.model_dump(mode="json") for c in impl.get_coupon(GetCouponIn(user_id=user_id))]


@mcp.tool()
def check_return_eligibility(order_id: str, item_id: str, reason: str) -> dict:
    """Check whether an item can be returned/refunded."""
    return impl.check_return_eligibility(
        CheckReturnEligibilityIn(order_id=order_id, item_id=item_id, reason=reason)
    ).model_dump(mode="json")


@mcp.tool()
def create_return_request(order_id: str, item_id: str, reason: str, idempotency_key: str) -> dict:
    """WRITE: create a return/refund ticket (idempotent on order_id+item_id)."""
    return impl.create_return_request(
        CreateReturnRequestIn(order_id=order_id, item_id=item_id, reason=reason,
                              idempotency_key=idempotency_key)
    ).model_dump(mode="json")


@mcp.tool()
def issue_compensation(user_id: str, reason: str, amount: float, idempotency_key: str) -> dict:
    """WRITE: issue goodwill compensation (idempotent on idempotency_key)."""
    return impl.issue_compensation(
        IssueCompensationIn(user_id=user_id, reason=reason, amount=amount,
                            idempotency_key=idempotency_key)
    ).model_dump(mode="json")


@mcp.tool()
def escalate_to_human(user_id: str, reason: str, transcript: str) -> dict:
    """Hand off to a human agent."""
    return impl.escalate_to_human(
        EscalateToHumanIn(user_id=user_id, reason=reason, transcript=transcript)
    ).model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
