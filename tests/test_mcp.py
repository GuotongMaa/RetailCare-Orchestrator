"""MCP layer: an independent client can list and call the exposed tools."""
import asyncio
import json

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


def test_mcp_call_get_order():
    seed(reset=True)
    result = asyncio.run(mcp.call_tool("get_order", {"order_id": "O1001"}))
    payload = json.loads(_text(result))
    assert payload["user_id"] == "u1"
    assert len(payload["items"]) == 2
