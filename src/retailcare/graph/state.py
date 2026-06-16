"""Agent state for the LangGraph StateGraph."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: Annotated[list[dict], operator.add]  # OpenAI-format chat messages
    user_id: str
    model: str
    steps: int  # tool-call rounds taken (loop guard)
    meta: dict[str, Any]  # carries trace + usage handles
