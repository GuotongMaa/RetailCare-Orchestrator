# Agent Engineering Glossary for RetailCare

## Agent

In this project, an agent is the model-driven loop in `graph/agent.py`. It reads
the conversation state, decides whether to call tools, receives tool results,
and eventually replies.

## Workflow

A workflow is the deterministic structure around the agent. In RetailCare this
is the LangGraph state graph: start at `agent`, route to `tools` when tool calls
exist, loop back to `agent`, and stop when there are no tool calls or the step
limit is reached.

## ReAct

ReAct means the model alternates between reasoning and acting. In code, the
visible version is `agent_node()` producing tool calls and `tools_node()`
returning observations. The private reasoning may stay inside the model, but the
action/observation loop is explicit.

## Tool Calling

Tool calling is how the model asks code to do something. RetailCare exposes
Pydantic schemas as OpenAI-style tool specs in `tools/registry.py`; the model
returns a tool name and JSON arguments; the runtime validates and dispatches.

## Tool Contract

A tool contract is the typed agreement between model-facing tool calls and code.
RetailCare uses Pydantic input and output models in `tools/schema.py`.

## Harness

A harness is the system that runs tasks, captures behavior, and scores outcomes.
RetailCare's harness is under `eval/`: it loads benchmark tasks, runs the agent,
collects traces, computes pass^k and compliance metrics, and writes reports.

## Loop

A loop is repeated execution until a stop condition. RetailCare's loop is
`agent -> tools -> agent`. `MAX_STEPS` prevents endless tool-calling.

## State

State is what the graph carries between nodes. RetailCare's `AgentState`
contains messages, user id, model name, step count, and metadata.

## Checkpoint

A checkpoint persists graph state so a conversation can resume. RetailCare uses
LangGraph's `SqliteSaver`, keyed by `thread_id`.

## Memory

Memory is information retained across turns or sessions. RetailCare has
short-term memory in checkpointed messages and derived summary memory in
`memory/summary.py`.

## Trace

A trace is a structured event log of a conversation: messages, tool calls, tool
results, guardrail decisions, interrupts, and errors. RetailCare uses
`trace/logger.py`.

## Guardrail

A guardrail is code that constrains risky behavior. In RetailCare, guardrails
re-check write tools against business rules and choose block, confirm, escalate,
or allow.

## HITL

Human-in-the-loop. RetailCare uses LangGraph `interrupt()` to pause low-value
eligible write actions until the user confirms.

## Idempotency

Idempotency means retrying the same action does not create duplicate side
effects. RetailCare deduplicates return tickets by order/item and write keys.

## RAG

Retrieval-augmented generation. RetailCare can retrieve versioned policy chunks
through `search_policy` instead of embedding policy directly in the prompt.

## MCP

Model Context Protocol. RetailCare exposes its tools through
`mcp_server/server.py`, so other MCP clients can reuse the same tool layer.

## Eval

An eval is a repeatable measurement of behavior. RetailCare has deterministic
guardrail evals and model-running task evals.

## Pass^k

Pass^k estimates consistency: for each task, how likely are k independent runs
to all succeed? RetailCare computes this in `eval/metrics.py`.
