"""Single ReAct agent as a LangGraph StateGraph (L0 baseline).

agent_node -> (tool calls?) -> tools_node -> agent_node -> ... -> END
Guardrails / HITL interrupt / policy RAG are layered on top in M2 (L1/L2).
"""
from __future__ import annotations

import json

import litellm
from langgraph.graph import END, START, StateGraph

from retailcare.config import LLMResult, settings, usage
from retailcare.graph.prompts import SYSTEM_L0
from retailcare.graph.state import AgentState
from retailcare.tools.registry import dispatch, openai_tools
from retailcare.trace.logger import Trace

MAX_STEPS = 8
_TOOLS = openai_tools()


def _trace(state: AgentState) -> Trace | None:
    return (state.get("meta") or {}).get("trace")


def agent_node(state: AgentState) -> dict:
    model = state.get("model") or settings.model
    resp = litellm.completion(
        model=f"openai/{model}",
        api_base=settings.base_url,
        api_key=settings.api_key,
        messages=state["messages"],
        tools=_TOOLS,
        tool_choice="auto",
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
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


def tools_node(state: AgentState) -> dict:
    tr = _trace(state)
    last = state["messages"][-1]
    out: list[dict] = []
    for tc in last.get("tool_calls", []):
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}
        if tr:
            tr.tool_call(name, args)
        result, err = dispatch(name, args)
        if err:
            if tr:
                tr.tool_error(name, err)
            content = json.dumps({"error": err})
        else:
            if tr:
                tr.tool_result(name, result if isinstance(result, dict) else {"result": result})
            content = json.dumps(result, default=str)
        out.append({"role": "tool", "tool_call_id": tc["id"], "name": name, "content": content})
    return {"messages": out}


def _route(state: AgentState) -> str:
    if state.get("steps", 0) >= MAX_STEPS:
        return END
    last = state["messages"][-1]
    return "tools" if last.get("tool_calls") else END


def build_agent():
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", _route, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    return g.compile()


def system_message(user_id: str) -> dict:
    return {"role": "system", "content": SYSTEM_L0.format(user_id=user_id)}
