# Architecture

RetailCare Orchestrator is an **evaluation-driven reliability system** for high-risk,
multi-turn e-commerce after-sales. The architecture is deliberately *restrained*: a
single ReAct agent over a typed tool layer, hardened with guardrails + HITL, and
surrounded by an evaluation harness that decides — with data — whether more structure
is worth it.

## Core doctrine

RetailCare is not designed as a rigid, pre-scripted workflow. It is a
**state-grounded ReAct orchestrator**:

- **ReAct-first:** the agent dynamically decides the next business action during the
  conversation, such as checking an order, tracking shipment, checking policy,
  clarifying missing information, requesting a refund, issuing compensation, or
  escalating a complaint.
- **LangGraph State-governed:** LangGraph is used primarily for shared state,
  checkpoint, interrupt, and resume. The state must keep the agent grounded in what is
  known, what was verified by tools, what is pending, and what has already happened,
  especially across long multi-turn conversations and business-context switches.
- **System-enforced safety:** model tool calls are treated as operation proposals, not
  final authority. The backend system decides whether an action executes through
  schemas, ownership checks, business policy, guardrails, HITL, idempotency, and audit.
  High-risk writes are checked before execution, never executed first and repaired
  afterward.

The main upgrade direction is therefore stronger business state and safer recovery,
not adding fixed nodes for their own sake. More nodes or subgraphs are justified only
when they improve state grounding, safety boundaries, evaluation clarity, or
maintainability.

## Topology derivation (why one agent, not seven)

Per the project definition, agent topology is an experimental outcome, not a premise:

- **L0** — single ReAct agent, all tools, policy in the prompt. (baseline / control)
- **L1** — same single agent, hardened: policy RAG, write guardrails, HITL confirm,
  idempotency, fault recovery. *No new agents.*
- **L2** — split refund into a dedicated subgraph **only if** the data shows systematic
  domain confusion after L1. (scoped as future work)

The M3 ablation (`reports/ablation_report.md`) shows L0→L1 lifts pass@1 0.633→0.80 and
cuts tool-selection errors 11→6 **without adding any agent** — evidence for "harden
first, split only on demand."

## Components

```
                 ┌─────────────────────────────────────────────┐
   user ──▶ FastAPI / CLI / demo                                │
                 │   Conversation runtime (multi-turn, HITL)    │
                 │   thread_id ── SqliteSaver checkpointer ──── cross-session resume
                 ▼                                               │
        LangGraph StateGraph                                     │
        ┌────────────┐   tool_calls   ┌──────────────────────┐  │
        │ agent_node │ ─────────────▶ │ tools_node           │  │
        │ (LiteLLM,  │ ◀───────────── │  guardrails (writes) │  │
        │  DeepSeek) │   tool results │  HITL interrupt()    │  │
        └────────────┘                │  recovery/retry      │  │
                                       └─────────┬────────────┘  │
                                                 ▼               │
                        tool registry  ──▶  typed impls (Pydantic)
                          │  (also exposed via MCP server)        │
          ┌──────────────┼───────────────┬──────────────┐        │
       read tools     write tools     policy RAG      audit       │
   get_order/...   create_return/...  (Chroma+ver)   (DB rows)     │
          └──────────────┴───────────────┴──────────────┘         │
                         SQLAlchemy ─ PostgreSQL (prod) / SQLite (dev)
                                                                   │
   trace (contextvar) ── structured JSON per tool/interrupt/decision ┘
```

### Key elements

- **Tool layer** (`tools/`): 8 tools with Pydantic I/O contracts; read (auto) vs write
  (high-risk). Single `registry` drives both the agent (OpenAI tool specs) and the
  **MCP server** (`mcp_server/`), so tools are reusable by any MCP client.
- **Agent graph** (`graph/`): `agent_node` (LiteLLM → DeepSeek v4, a reasoning model) and
  `tools_node`. Writes pass through **guardrails** (block / confirm / escalate / allow);
  `confirm` raises LangGraph **`interrupt()`** for human-in-the-loop, resumable from the
  **checkpointer** (and across sessions via a stable `thread_id`).
- **Idempotency**: returns dedup on `(order_id, item_id)`; compensation on
  `idempotency_key`. Retries / double-clicks never double-act.
- **Policy RAG** (`policy/`): Chroma (ONNX MiniLM embedding, no torch) over versioned
  policy chunks; lexical fallback. Citations (chunk id + version) flow into the trace.
- **Fault recovery** (`tools/recovery.py`): bounded retry on transient faults → graceful
  degradation + escalation; stale data flagged.
- **Memory** (`memory/`): short-term = checkpointed message list; ticket-state summary
  derived from the trace for cheap long-context continuity.
- **Trace** (`trace/`): every tool call / interrupt / guardrail decision / failure logged
  as structured JSON (UI + error-taxonomy input). Held in a contextvar so the checkpointer
  only serializes plain values.
- **Eval** (`eval/`): action-level success, **pass^k** + Wilson CI, compliance metrics,
  8-class error taxonomy, LLM-as-judge screen, ablation experiments, and a **model-free
  regression gate** wired into CI.

## Data layer

SQLAlchemy abstracts the backend: **PostgreSQL** in prod (via `docker compose`, verified),
**SQLite** for dev/tests/eval (each eval process isolated in its own temp DB). Swapping is
a `DATABASE_URL` change.

## Model layer

LiteLLM against an OpenAI-compatible endpoint. DeepSeek v4 (`-flash` weak / `-pro` strong)
are reasoning models: generous `max_tokens`, answer read from `content`; token/cost tracked
per call for the cost-aware (Pareto) view.

## Reliability acceptance (the 6 "enterprise closed-loop" checks)

real business rules · end-to-end runnable · observable (trace) · recoverable
(checkpoint/HITL) · evaluable (benchmark) · regression-guarded (CI). See
`OPERATIONS_MANUAL.md` §2 for the evidence mapping.
