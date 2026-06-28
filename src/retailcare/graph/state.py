"""Agent state for the LangGraph StateGraph.

Two-layer design (see the upgrade design notes):
- These structured fields are the **single source of truth**; code reads them for
  control. Single-value fields use overwrite semantics (last write wins); evidence
  that should accumulate (`findings`) uses a merge reducer.
- The *digest* shown to the model is a one-shot projection of this state, rendered
  fresh each turn and never stored here (see graph/digest.py).

Trust boundary: `user_id`/`thread_id` are injected by the system (session), never
supplied or modifiable by the model.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def merge_dict(old: dict | None, new: dict | None) -> dict:
    """Reducer: accumulate evidence instead of clobbering it.

    `{**old, **new}` so a later turn's findings for item B merge into the existing
    findings for item A rather than replacing them.
    """
    out = dict(old or {})
    out.update(new or {})
    return out


class AgentState(TypedDict, total=False):
    messages: Annotated[list[dict], operator.add]  # OpenAI-format chat messages (append)
    # --- trusted, system-injected (model cannot set) ---
    user_id: str
    thread_id: str
    model: str
    steps: int  # tool-call rounds taken (loop guard)
    # --- structured working memory (overwrite unless noted) ---
    intent: str | None                 # order_status|shipping|returns|compensation|complaint
    focus: dict                        # {order_id, item_id?} currently in scope
    focus_stack: list[dict]            # shallow stack of prior foci (cross-order switches)
    plan: list[dict]                   # [{step, status}] checklist
    task_status: str                   # gathering_info|awaiting_confirmation|escalated|resolved
    pending_action: dict | None        # gated write awaiting confirmation {tool,args,token}
    findings: Annotated[dict, merge_dict]  # cached verified results, keyed by item_id (merge)
    meta: dict[str, Any]               # carries trace + usage handles
