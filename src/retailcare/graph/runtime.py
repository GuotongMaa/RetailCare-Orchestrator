"""Conversation runtime around the compiled agent graph (multi-turn + trace)."""
from __future__ import annotations

from retailcare.config import settings
from retailcare.graph.agent import build_agent, system_message
from retailcare.trace.logger import Trace

_AGENT = build_agent()


class Conversation:
    def __init__(self, user_id: str, model: str | None = None, trace: Trace | None = None):
        self.user_id = user_id
        self.model = model or settings.model
        self.trace = trace or Trace()
        self.messages: list[dict] = [system_message(user_id)]

    def send(self, text: str) -> str:
        self.trace.log("message", "user", text=text)
        self.messages.append({"role": "user", "content": text})
        result = _AGENT.invoke(
            {"messages": self.messages, "user_id": self.user_id, "model": self.model,
             "steps": 0, "meta": {"trace": self.trace}},
            config={"recursion_limit": 50},
        )
        # result["messages"] is the full accumulated list (input + new); adopt it.
        self.messages = result["messages"]
        reply = self.messages[-1].get("content", "")
        self.trace.log("message", "assistant", text=reply)
        return reply
