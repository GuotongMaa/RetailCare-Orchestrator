"""Single ReAct agent as a LangGraph StateGraph, hardened with guardrails + HITL (L1).

agent_node -> (tool calls?) -> tools_node -> agent_node -> ... -> END

Trust boundary (the upgrade design notes):
- Identity (`user_id`) and write idempotency keys are INJECTED by the system from
  trusted session state, never taken from the model's tool arguments (D2/D3).
- The model receives a one-shot `state digest` each turn for orientation; it is
  never persisted into the message history (D1).

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
from retailcare.graph.digest import (
    action_token,
    apply_tool_effect,
    derive_idempotency_key,
    render_digest,
)
from retailcare.graph.guardrails import guard_write
from retailcare.graph.prompts import SYSTEM_L0
from retailcare.graph.state import AgentState
from retailcare.tools.recovery import call_with_recovery
from retailcare.tools.registry import GATED_TOOLS, REGISTRY, openai_tools
from retailcare.trace.logger import Trace, get_current

MAX_STEPS = 8
_APPROVALS = {"yes", "y", "approve", "approved", "confirm", "confirmed", "ok", "true"}
_TOOLS = openai_tools()


def _trace(state: AgentState) -> Trace | None:
    return get_current()


def _approved(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _APPROVALS


def _resume_ok(decision, token: str) -> bool:
    """Validate an HITL resume value against the action it should authorize (D7).

    Accepts a bare yes/no (back-compat) or a dict {"decision":..., "token":...}.
    If a token is supplied it must match the action's token, else fail-closed —
    a 'yes' can never bind to a different action than the one the user confirmed.
    """
    if isinstance(decision, dict):
        if "token" in decision and decision.get("token") != token:
            return False
        return _approved(decision.get("decision"))
    return _approved(decision)


def agent_node(state: AgentState) -> dict:
    model = state.get("model") or settings.model
    # D1: render a fresh state digest and inject it for THIS call only — it is not
    # added to state["messages"], so the history never accumulates stale snapshots.
    call_messages = list(state["messages"])
    digest = render_digest(state)
    if digest:
        call_messages.append({"role": "system", "content": digest})
    resp = litellm.completion(
        model=f"openai/{model}", api_base=settings.base_url, api_key=settings.api_key,
        messages=call_messages, tools=_TOOLS, tool_choice="auto",
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


def _inject_server_fields(name: str, args: dict, state: AgentState) -> str | None:
    """Overwrite identity + idempotency from trusted session state (D2/D3).

    Returns an error string if a customer-scoped tool has no authenticated user
    (fail-closed), else None. Mutates `args` in place.
    """
    fields = REGISTRY[name].input_model.model_fields
    if "user_id" in fields:
        uid = state.get("user_id")
        if not uid:
            return "no authenticated user in session; cannot run customer-scoped tool"
        args["user_id"] = uid  # authoritative — ignores anything the model put here
    if "idempotency_key" in fields:
        args["idempotency_key"] = derive_idempotency_key(state.get("thread_id"), name, args)
    return None


def _merge_effect(acc: dict, effect: dict) -> None:
    for k, v in effect.items():
        if k == "findings":
            acc["findings"] = {**acc.get("findings", {}), **v}
        else:
            acc[k] = v


def tools_node(state: AgentState) -> dict:
    tr = _trace(state)
    meta = state.get("meta") or {}
    auto_confirm = bool(meta.get("auto_confirm", False))
    guardrails = bool(meta.get("guardrails", True))  # L0 ablation sets this False
    last = state["messages"][-1]
    out: list[dict] = []
    acc: dict = {}  # accumulated structured-state updates for this turn
    hitl_used = False  # D7: gate at most ONE confirm-write per node run
    for tc in last.get("tool_calls", []):
        name = tc["function"]["name"]
        tc_id = tc["id"]
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}
        if name not in REGISTRY:
            out.append(_tool_msg(tc_id, name, {"error": f"unknown tool: {name}"}))
            continue

        # Trust boundary: system owns identity + idempotency, not the model.
        inj_err = _inject_server_fields(name, args, state)
        if inj_err:
            out.append(_tool_msg(tc_id, name, {"error": inj_err}))
            continue

        if guardrails and name in GATED_TOOLS:
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
                # D7: only one write may be in HITL confirmation per node run. Any
                # further confirm-writes are deferred so a single resume can never
                # be matched (by interrupt position) to the wrong action.
                if hitl_used:
                    out.append(_tool_msg(tc_id, name, {"deferred": True,
                               "reason": "another action is awaiting confirmation; "
                                         "retry this one on the next turn"}))
                    continue
                token = action_token(state.get("thread_id"), name, args)
                if tr:
                    tr.decision("await_confirmation", tool=name, token=token)
                decision = interrupt({
                    "type": "confirm_write", "tool": name, "args": args,
                    "refund_amount": d.refund_amount, "reason": d.reason, "token": token,
                    "prompt": f"Confirm {name} for ${d.refund_amount}? (yes/no)"})
                hitl_used = True
                if not _resume_ok(decision, token):
                    if tr:
                        tr.decision("user_declined", tool=name)
                    out.append(_tool_msg(tc_id, name, {"declined": True,
                               "reason": "customer did not confirm the action"}))
                    continue
                if tr:
                    tr.decision("user_confirmed", tool=name)

        # execute: reads, escalate_to_human, or an approved/auto-confirmed write
        if tr:
            tr.tool_call(name, args)
        result, err = call_with_recovery(name, args, trace=tr)
        if err:
            if tr:
                tr.tool_error(name, err)
            out.append(_tool_msg(tc_id, name, {"error": err}))
        else:
            payload = result if isinstance(result, dict) else {"result": result}
            if tr:
                tr.tool_result(name, payload)
            out.append(_tool_msg(tc_id, name, payload))
        # D5: advance structured state only from verified tool facts.
        view = {**state, **acc}
        _merge_effect(acc, apply_tool_effect(view, name, args, result, err))
    return {"messages": out, **acc}


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
    return {"role": "system", "content": SYSTEM_L0}
