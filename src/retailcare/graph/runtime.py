"""Conversation runtime: multi-turn, HITL confirm/resume, cross-session persistence.

A persistent SqliteSaver checkpointer keys state by thread_id, so a customer can
come back the next day (new process) and resume the same ticket. The live Trace
is passed via contextvar, never stored in checkpointed state.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from retailcare.config import settings
from retailcare.graph.agent import build_agent
from retailcare.graph.prompts import system_for
from retailcare.trace.logger import Trace, set_current

# Configurable so concurrent eval processes can isolate their checkpoint store.
_CKPT_PATH = os.getenv("CHECKPOINT_DB", "retailcare_checkpoints.db")
_conn = sqlite3.connect(_CKPT_PATH, check_same_thread=False)
_saver = SqliteSaver(_conn)
try:
    _saver.setup()
except Exception:  # noqa: BLE001 - setup is idempotent across versions
    pass
_AGENT = build_agent(checkpointer=_saver)


@dataclass
class TurnResult:
    reply: str
    interrupted: bool = False
    interrupt: dict | None = None


class Conversation:
    """thread_id identifies the durable ticket; reuse it to resume across sessions."""

    def __init__(self, user_id: str, model: str | None = None, auto_confirm: bool = False,
                 trace: Trace | None = None, thread_id: str | None = None,
                 guardrails: bool = True, policy_mode: str = "prompt"):
        self.user_id = user_id
        self.model = model or settings.model
        self.auto_confirm = auto_confirm
        self.guardrails = guardrails          # L0 ablation: False
        self.policy_mode = policy_mode         # "prompt" | "rag"
        self.trace = trace or Trace()
        self.thread_id = thread_id or self.trace.session_id
        self._started = False

    @property
    def _config(self) -> dict:
        return {"configurable": {"thread_id": self.thread_id}, "recursion_limit": 50}

    def _invoke(self, payload) -> TurnResult:
        set_current(self.trace)
        result = _AGENT.invoke(payload, config=self._config)
        return self._wrap(result)

    def send(self, text: str) -> TurnResult:
        self.trace.log("message", "user", text=text)
        if not self._started:
            msgs = [system_for(self.policy_mode, self.user_id), {"role": "user", "content": text}]
            self._started = True
        else:
            msgs = [{"role": "user", "content": text}]
        return self._invoke({
            "messages": msgs, "user_id": self.user_id, "model": self.model,
            "steps": 0, "meta": {"auto_confirm": self.auto_confirm, "guardrails": self.guardrails},
        })

    def confirm(self, decision) -> TurnResult:
        """Resume a HITL-paused conversation with the user's decision (yes/no/bool)."""
        return self._invoke(Command(resume=decision))

    def _wrap(self, result) -> TurnResult:
        interrupts = result.get("__interrupt__")
        if interrupts:
            payload = interrupts[0].value
            payload = payload if isinstance(payload, dict) else {"value": payload}
            self.trace.interrupt("confirm_write", **payload)
            return TurnResult(reply="", interrupted=True, interrupt=payload)
        reply = result["messages"][-1].get("content", "")
        self.trace.log("message", "assistant", text=reply)
        return TurnResult(reply=reply)


def resume_existing(thread_id: str, user_id: str, trace: Trace | None = None) -> Conversation:
    """Reattach to a persisted ticket (cross-session). _started=True skips the system msg."""
    conv = Conversation(user_id=user_id, trace=trace, thread_id=thread_id)
    conv._started = True
    return conv


def checkpoint_path() -> Path:
    return Path(_CKPT_PATH)
