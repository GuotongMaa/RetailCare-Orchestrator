"""MCP layer: an independent client can list and call the exposed tools."""
import asyncio
import json
import os

import pytest

from retailcare.data.seed import seed
from retailcare.mcp_server.server import mcp


def _text(result):
    # FastMCP returns (content_list, ...) or content list; normalize to text.
    content = result[0] if isinstance(result, tuple) else result
    parts = []
    for c in content:
        parts.append(getattr(c, "text", "") or "")
    return "".join(parts)


def test_mcp_lists_eight_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {
        "get_order", "get_shipment", "search_policy", "get_coupon",
        "check_return_eligibility", "create_return_request",
        "issue_compensation", "escalate_to_human",
    } <= names


def test_mcp_get_order_uses_bound_principal_not_arg():
    # Identity is bound by the host (RETAILCARE_MCP_USER), not a tool argument (C6).
    seed(reset=True)
    os.environ["RETAILCARE_MCP_USER"] = "u1"
    try:
        result = asyncio.run(mcp.call_tool("get_order", {"order_id": "O1001"}))
    finally:
        os.environ.pop("RETAILCARE_MCP_USER", None)
    payload = json.loads(_text(result))
    assert payload["user_id"] == "u1"
    assert len(payload["items"]) == 2


def test_mcp_fails_closed_without_bound_principal():
    seed(reset=True)
    os.environ.pop("RETAILCARE_MCP_USER", None)
    with pytest.raises(Exception):  # noqa: B017 - any failure is fine; must not return data
        asyncio.run(mcp.call_tool("get_order", {"order_id": "O1001"}))
