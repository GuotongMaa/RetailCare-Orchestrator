"""MCP server exposing the after-sales tool layer (2026 standard tool contract).

Run as a stdio MCP server:   python -m retailcare.mcp_server.server
The same typed implementations back both the in-process agent and this server,
so tools are reusable by any MCP-capable client/IDE.

TRUST BOUNDARY (docs/state-and-security-upgrade.md D11/C6): identity is bound by the
SERVER, not the caller. The MCP host authenticates the principal of the connection and
exposes it as `RETAILCARE_MCP_USER`; tools read that via `_mcp_user()` and the customer
id is NEVER a tool argument — exactly like the in-process agent injects `user_id` from
trusted session state. A client/model therefore cannot act on another customer's data.
Deployment: the host launches one server (process) per authenticated user with
`RETAILCARE_MCP_USER` set; fail-closed if it is missing.
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from retailcare.graph.digest import derive_idempotency_key
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


def _mcp_user() -> str:
    """Trusted customer id bound by the host (not the caller). Fail-closed."""
    uid = os.getenv("RETAILCARE_MCP_USER")
    if not uid:
        raise ValueError("RETAILCARE_MCP_USER not set: the MCP host must bind the "
                         "authenticated principal before serving customer-scoped tools")
    return uid


def _mcp_session() -> str:
    """Session scope for system-derived idempotency keys. The host may set
    RETAILCARE_MCP_SESSION per ticket; otherwise we scope to the bound user."""
    return os.getenv("RETAILCARE_MCP_SESSION") or _mcp_user()


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Fetch the authenticated customer's order and items by order_id."""
    return impl.get_order(GetOrderIn(user_id=_mcp_user(), order_id=order_id)).model_dump(mode="json")


@mcp.tool()
def get_shipment(order_id: str) -> dict:
    """Fetch shipment/tracking status for the authenticated customer's order."""
    return impl.get_shipment(
        GetShipmentIn(user_id=_mcp_user(), order_id=order_id)
    ).model_dump(mode="json")


@mcp.tool()
def search_policy(query: str, k: int = 3) -> list[dict]:
    """Search the after-sales policy; returns versioned chunks."""
    return [c.model_dump(mode="json") for c in impl.search_policy(SearchPolicyIn(query=query, k=k))]


@mcp.tool()
def get_coupon() -> list[dict]:
    """List the authenticated customer's coupons."""
    return [c.model_dump(mode="json") for c in impl.get_coupon(GetCouponIn(user_id=_mcp_user()))]


@mcp.tool()
def check_return_eligibility(order_id: str, item_id: str, reason: str) -> dict:
    """Check whether the authenticated customer's item can be returned/refunded."""
    return impl.check_return_eligibility(
        CheckReturnEligibilityIn(user_id=_mcp_user(), order_id=order_id, item_id=item_id,
                                 reason=reason)
    ).model_dump(mode="json")


@mcp.tool()
def create_return_request(order_id: str, item_id: str, reason: str) -> dict:
    """WRITE: create a return/refund ticket for the authenticated customer's order.
    The idempotency key is system-derived (not a caller argument) — same as the
    in-process agent (D3)."""
    uid = _mcp_user()
    args = {"user_id": uid, "order_id": order_id, "item_id": item_id}
    key = derive_idempotency_key(_mcp_session(), "create_return_request", args)
    return impl.create_return_request(
        CreateReturnRequestIn(user_id=uid, order_id=order_id, item_id=item_id,
                              reason=reason, idempotency_key=key)
    ).model_dump(mode="json")


@mcp.tool()
def issue_compensation(reason: str, amount: float) -> dict:
    """WRITE: issue goodwill compensation to the authenticated customer.
    Idempotency key is system-derived from (session, user, reason, amount) (D3)."""
    uid = _mcp_user()
    args = {"user_id": uid, "reason": reason, "amount": amount}
    key = derive_idempotency_key(_mcp_session(), "issue_compensation", args)
    return impl.issue_compensation(
        IssueCompensationIn(user_id=uid, reason=reason, amount=amount, idempotency_key=key)
    ).model_dump(mode="json")


@mcp.tool()
def escalate_to_human(reason: str, transcript: str) -> dict:
    """Hand off the authenticated customer's conversation to a human agent."""
    return impl.escalate_to_human(
        EscalateToHumanIn(user_id=_mcp_user(), reason=reason, transcript=transcript)
    ).model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
