# RetailCare Project Map

RetailCare Orchestrator is an agent engineering demo for e-commerce after-sales
support. Its strongest learning value is that it connects agent behavior to
business rules, tool correctness, human approval, tracing, and evaluation.

## Architecture in One Sentence

A FastAPI/CLI conversation runtime sends user messages into a LangGraph
single-agent loop; the agent can call typed tools; write tools are guarded by
policy checks and human confirmation; every action is traced and later evaluated.

## Main Runtime Flow

```text
user/API/CLI
  -> retailcare.graph.runtime.Conversation.send()
  -> LangGraph compiled agent
  -> agent_node(): model call with OpenAI-style tool specs
  -> tools_node(): parse tool calls and enforce guardrails
  -> tools.recovery.call_with_recovery()
  -> tools.registry.dispatch()
  -> tools.impl business logic
  -> SQLAlchemy database / policy store / trace logger
  -> tool result back to model
  -> final assistant reply or HITL interrupt
```

## Key Directories

`src/retailcare/graph/`

Agent orchestration. Contains the LangGraph state, prompt templates, agent node,
tool node, guardrails, checkpointer-backed runtime, and resume logic.

`src/retailcare/tools/`

Tool contracts and implementations. `schema.py` defines Pydantic input/output
models, `registry.py` exposes OpenAI-style function specs and dispatch, and
`impl.py` performs database-backed business operations.

`src/retailcare/data/`

Mock e-commerce backend. SQLAlchemy models define orders, items, shipments,
coupons, tickets, compensations, and audit logs. `seed.py` creates deterministic
cases for tests and evals.

`src/retailcare/policy/`

Policy store and RAG search. This supports versioned policy grounding and lets
the project compare prompt-embedded policy vs retrieved policy.

`src/retailcare/memory/`

Derived ticket summary memory. It turns trace events into a compact state
summary without storing a non-serializable trace inside LangGraph state.

`src/retailcare/trace/`

Structured trace events for messages, tool calls, tool results, guardrail
decisions, interruptions, and errors.

`src/retailcare/api/`

FastAPI service exposing `/chat`, `/confirm`, `/trace/{session}`, `/health`, and
the static web UI.

`src/retailcare/mcp_server/`

MCP tool server. It exposes the same typed tool implementations to external MCP
clients.

`eval/`

Evaluation harness. Includes task loading, per-task runs, pass^k metrics,
compliance metrics, error taxonomy, BFCL-style tool tests, ablations, and a
model-free regression gate.

`tests/`

No-network tests for tools, memory, guardrails/faults, HITL, metrics, MCP, and
basic smoke checks.

`reports/`

Generated or curated reports for baseline quality, ablations, BFCL, Pareto
quality/cost, error taxonomy, and demo transcripts.

## Core Concepts in This Codebase

Agent: the model loop in `graph/agent.py` that decides whether to answer or call
tools.

Workflow: the deterministic graph and runtime around the model loop, especially
LangGraph nodes, edges, state, and stop conditions.

Tool calling: the model emits function calls matching `tools/registry.py`; code
validates arguments with Pydantic and dispatches to `tools/impl.py`.

Guardrail: code in `graph/guardrails.py` that re-checks risky write actions
against policy before execution.

HITL: LangGraph `interrupt()` pauses a write action until a human/user confirms.

Harness: the eval infrastructure under `eval/`, especially `eval/runner.py`,
`eval/common.py`, and `eval/metrics.py`.

Loop: the repeated `agent -> tools -> agent` cycle, limited by `MAX_STEPS`.

## Tool Inventory

Read tools:

- `get_order`
- `get_shipment`
- `search_policy`
- `get_coupon`
- `check_return_eligibility`

Write/high-risk tools:

- `create_return_request`
- `issue_compensation`
- `escalate_to_human`

Important rule: write tools need idempotency keys and pass through guardrails.

## Business Risk Model

The hero flow is returns/refunds. The business rules in `BUSINESS_RULES.md`
create a simple but realistic safety model:

- Low-value eligible refund: ask for confirmation, then create the return.
- High-value refund at or above 200 USD: escalate to a human.
- Defective/damaged item: escalate to a human.
- Non-returnable, not delivered, unknown, or out of window: block or clarify.
- Tool failure or stale state: retry, degrade safely, then escalate.

## Evaluation Model

Two evaluation layers matter:

- Deterministic safety regression: `eval/regression.py`.
- Agent benchmark loop: `eval/runner.py` over `eval/datasets/refund_tasks.jsonl`.

The deterministic gate is useful early because it teaches policy correctness
without needing model credentials. The benchmark loop is useful later because it
measures whether the agent chooses the right actions under realistic prompts.
