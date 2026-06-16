"""Single ReAct agent as a LangGraph StateGraph, hardened with guardrails + HITL (L1).

agent_node -> (tool calls?) -> tools_node -> agent_node -> ... -> END

Write tools pass through guardrails (BUSINESS_RULES §4):
- block:    not executed; model is told why.
- escalate: not executed; model is told to hand off to a human.
- confirm:  HITL — interrupt() pauses for user confirmation (unless meta.auto_confirm),
            then executes on approval. Idempotent tools make node re-run on resume safe.
"""
from __future__ import annotations

import json

import litellm
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from retailcare.config import LLMResult, settings, usage
from retailcare.graph.guardrails import guard_write
from retailcare.graph.prompts import SYSTEM_L0
from retailcare.graph.state import AgentState
from retailcare.tools.recovery import call_with_recovery
from retailcare.tools.registry import openai_tools
from retailcare.trace.logger import Trace, get_current

MAX_STEPS = 8
_GATED = {"create_return_request", "issue_compensation"}
_APPROVALS = {"yes", "y", "approve", "approved", "confirm", "confirmed", "ok", "true"}
_TOOLS = openai_tools()


def _trace(state: AgentState) -> Trace | None:
    return get_current()


def _approved(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _APPROVALS


def agent_node(state: AgentState) -> dict:
    model = state.get("model") or settings.model
    resp = litellm.completion(
        model=f"openai/{model}", api_base=settings.base_url, api_key=settings.api_key,
        messages=state["messages"], tools=_TOOLS, tool_choice="auto",
        temperature=settings.temperature, max_tokens=settings.max_tokens,
    )
    msg = resp.choices[0].message
    u = resp.usage
    usage.add(LLMResult(
        content=msg.content or "", reasoning=getattr(msg, "reasoning_content", "") or "",
        model=model, prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(u, "completion_tokens", 0) or 0, latency_s=0.0,
    ))
    assistant: dict = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        assistant["tool_calls"] = [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]
    return {"messages": [assistant], "steps": state.get("steps", 0) + 1}


def _tool_msg(tc_id: str, name: str, payload: dict) -> dict:
    return {"role": "tool", "tool_call_id": tc_id, "name": name,
            "content": json.dumps(payload, default=str)}


def tools_node(state: AgentState) -> dict:
    tr = _trace(state)
    auto_confirm = bool((state.get("meta") or {}).get("auto_confirm", False))
    last = state["messages"][-1]
    out: list[dict] = []
    for tc in last.get("tool_calls", []):
        name = tc["function"]["name"]
        tc_id = tc["id"]
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}

        if name in _GATED:
            d = guard_write(name, args)
            if tr:
                tr.decision("guardrail", tool=name, action=d.action, reason=d.reason,
                            refund_amount=d.refund_amount, policy_versions=d.policy_versions)
            if d.action == "block":
                out.append(_tool_msg(tc_id, name, {"blocked": True, **d.as_tool_payload()}))
                continue
            if d.action == "escalate":
                out.append(_tool_msg(tc_id, name, {
                    "blocked": True, "requires_human": True, **d.as_tool_payload(),
                    "instruction": "Do not retry this write. Call escalate_to_human with the "
                                   "order/item details and a transcript."}))
                continue
            if d.action == "confirm" and not auto_confirm:
                decision = interrupt({
                    "type": "confirm_write", "tool": name, "args": args,
                    "refund_amount": d.refund_amount, "reason": d.reason,
                    "prompt": f"Confirm {name} for ${d.refund_amount}? (yes/no)"})
                if not _approved(decision):
                    if tr:
                        tr.decision("hitl", "user_declined", tool=name)
                    out.append(_tool_msg(tc_id, name, {"declined": True,
                               "reason": "customer did not confirm the action"}))
                    continue
                if tr:
                    tr.decision("hitl", "user_confirmed", tool=name)

        # execute: reads, escalate_to_human, or an approved/auto-confirmed write
        if tr:
            tr.tool_call(name, args)
        result, err = call_with_recovery(name, args, trace=tr)
        if err:
            if tr:
                tr.tool_error(name, err)
            out.append(_tool_msg(tc_id, name, {"error": err}))
        else:
            if tr:
                tr.tool_result(name, result if isinstance(result, dict) else {"result": result})
            out.append(_tool_msg(tc_id, name, result if isinstance(result, dict)
                                 else {"result": result}))
    return {"messages": out}


def _route(state: AgentState) -> str:
    if state.get("steps", 0) >= MAX_STEPS:
        return END
    last = state["messages"][-1]
    return "tools" if last.get("tool_calls") else END


def build_agent(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", _route, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    return g.compile(checkpointer=checkpointer)


def system_message(user_id: str) -> dict:
    return {"role": "system", "content": SYSTEM_L0.format(user_id=user_id)}
