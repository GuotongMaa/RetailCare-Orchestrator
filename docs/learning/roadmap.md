# Handbook-Driven RetailCare Learning Plan

The learning goal is simple:

> For each chapter of `海云大模型AIAgent应用面试通关手册.pdf`, connect the
> handbook concepts to the actual RetailCare architecture, code, tests, traces,
> and interview story.

RetailCare is studied as an AI Agent system, using the handbook as the
conceptual spine and RetailCare as the runnable implementation.

## Study Loop For Every Chapter

Each chapter session follows the same loop:

1. Search the handbook corpus and cite the relevant PDF pages.
2. Extract the chapter's key knowledge points, including Chinese/English terms.
3. For each important point, find a RetailCare proof example: code, architecture
   doc, business rule, test, eval, trace, report, or concrete scenario.
4. Explain why RetailCare uses this design and what alternatives were available.
5. Write one session note using the reusable knowledge-point card template.
6. Convert the understanding into an interview-ready explanation grounded in
   concrete project evidence.

Reusable card:

```text
知识点 -> 中英对照 -> 资料依据 -> RetailCare 例子 -> 具体场景
-> 项目证据 -> 为什么这样设计 -> 替代方案 -> 局限与扩展 -> 面试表达
```

Use the local retriever before each session:

```bash
python3 learning_lab/rag/search_agent_handbook.py "关键词" --top 5
```

## Chapter 01: AI Agent 基础概念

Handbook pages: 10-25

Learning question: RetailCare 为什么是 Agent，而不是普通 chatbot 或单次 LLM
调用?

RetailCare anchors:

- `README.md`
- `ARCHITECTURE.md`
- `BUSINESS_RULES.md`
- `src/retailcare/graph/agent.py`
- `src/retailcare/graph/runtime.py`
- `src/retailcare/graph/state.py`
- `src/retailcare/graph/prompts.py`
- `src/retailcare/demo.py`
- `tests/test_smoke.py`

Practice:

- Trace one customer request from `Conversation.send()` to model response.
- Identify the project's `LLM + Planning + Memory + Tools` components.
- Explain the difference between "answering text" and "closed-loop task
  completion" in RetailCare.

Deliverable:

- A one-page map: `Agent concept -> RetailCare implementation -> evidence file`.

## Chapter 02: 核心框架

Handbook pages: 26-53

Learning question: RetailCare 的 LangGraph/ReAct 循环如何落地? 为什么当前项目
以单 Agent 图为基线?

RetailCare anchors:

- `src/retailcare/graph/agent.py`
- `src/retailcare/graph/runtime.py`
- `src/retailcare/graph/state.py`
- `src/retailcare/graph/prompts.py`
- `src/retailcare/graph/guardrails.py`
- `reports/demo_transcript.md`
- `reports/ablation_report.md`
- `eval/experiments/run_ablations.py`

Practice:

- Draw `agent -> tools -> agent` loop, including `_route()` and `MAX_STEPS`.
- Compare handbook ReAct / Plan-and-Execute / Reflexion to the actual
  implementation.
- Explain why RetailCare hardens one graph before adding specialist agents.

Deliverable:

- A graph-level explanation of nodes, edges, stop conditions, and failure paths.

## Chapter 03: RAG 技术

Handbook pages: 54-84

Learning question: RetailCare 如何把业务政策变成可检索、可引用、可评测的证据?

RetailCare anchors:

- `src/retailcare/policy/store.py`
- `src/retailcare/policy/rag.py`
- `src/retailcare/tools/impl.py`
- `src/retailcare/tools/schema.py`
- `src/retailcare/graph/prompts.py`
- `BUSINESS_RULES.md`
- `eval/datasets/refund_tasks.jsonl`
- `tests/test_tools.py`

Practice:

- Trace `search_policy` from tool schema to implementation to policy chunks.
- Compare lexical fallback and Chroma retrieval.
- Explain why policy chunk versions matter for auditability.
- Connect RAG risks from the handbook to RetailCare: stale policy, wrong chunk,
  missing citation, cross-user leakage, and prompt injection.

Deliverable:

- A RAG pipeline note: `policy text -> chunks -> retrieval -> tool result ->
  model decision -> trace/eval evidence`.

## Chapter 04: 工具调用

Handbook pages: 85-110

Learning question: RetailCare 如何让 Agent 安全地调用订单、物流、退货、优惠券和
人工升级工具?

RetailCare anchors:

- `src/retailcare/tools/schema.py`
- `src/retailcare/tools/registry.py`
- `src/retailcare/tools/impl.py`
- `src/retailcare/tools/recovery.py`
- `src/retailcare/tools/faults.py`
- `src/retailcare/mcp_server/server.py`
- `tests/test_tools.py`
- `tests/test_mcp.py`
- `tests/test_faults.py`

Practice:

- Build a matrix of all 8 tools: input schema, output schema, read/write risk,
  guardrail requirement, and idempotency behavior.
- Trace one successful read tool and one guarded write tool.
- Compare OpenAI-style Function Calling and MCP exposure in this project.

Deliverable:

- A tool contract and safety matrix suitable for interview explanation.

## Chapter 05: 记忆系统

Handbook pages: 111-133

Learning question: RetailCare 的短期状态、长期恢复和摘要记忆分别在哪里?

RetailCare anchors:

- `src/retailcare/graph/state.py`
- `src/retailcare/graph/runtime.py`
- `src/retailcare/memory/summary.py`
- `src/retailcare/trace/logger.py`
- `tests/test_memory.py`
- `retailcare_checkpoints.db`

Practice:

- Explain what goes into LangGraph checkpoint state and what stays outside it.
- Trace `thread_id`, `resume_existing()`, `confirm()`, and HITL resume.
- Explain the difference between message history, checkpoint persistence, trace,
  and derived ticket summary.

Deliverable:

- A memory boundary diagram: `conversation state`, `checkpoint`, `trace`,
  `summary`, and `business database`.

## Chapter 06: 多智能体系统

Handbook pages: 134-155

Learning question: RetailCare 什么时候需要多 Agent，什么时候单 Agent 更可靠?

RetailCare anchors:

- `ARCHITECTURE.md`
- `reports/ablation_report.md`
- `eval/experiments/run_ablations.py`
- `eval/experiments/pareto.py`
- `eval/error_taxonomy.py`
- `reports/error_taxonomy.md`
- `src/retailcare/graph/agent.py`

Practice:

- Compare possible specialist agents: refund, logistics, coupon, complaint, QA.
- Use eval and ablation reports to argue for or against splitting the graph.
- Identify handoff boundaries and coordination failure modes.

Deliverable:

- A multi-agent decision memo: "Keep single agent now / split later if metric X
  fails."

## Chapter 07: 大模型基础

Handbook pages: 156-177

Learning question: 模型能力、上下文、温度、成本、延迟如何影响 RetailCare 的架构
选择?

RetailCare anchors:

- `src/retailcare/config.py`
- `src/retailcare/graph/prompts.py`
- `src/retailcare/graph/agent.py`
- `eval/metrics.py`
- `eval/runner.py`
- `requirements.txt`
- `.env.example`

Practice:

- Explain `model`, `temperature`, `max_tokens`, usage accounting, and provider
  configuration.
- Connect model limitations to guardrails and tool verification.
- Explain why business facts should come from tools/RAG instead of model memory.

Deliverable:

- A model decision table: capability, cost, latency, safety risk, fallback plan.

## Chapter 08: 工程化实践

Handbook pages: 178-203

Learning question: RetailCare 如何从 demo 变成可追踪、可评测、可恢复的工程系统?

RetailCare anchors:

- `eval/datasets/refund_tasks.jsonl`
- `eval/common.py`
- `eval/runner.py`
- `eval/metrics.py`
- `eval/regression.py`
- `eval/judge.py`
- `src/retailcare/trace/logger.py`
- `src/retailcare/api/app.py`
- `Dockerfile`
- `docker-compose.yml`
- `OPERATIONS_MANUAL.md`
- `tests/`

Practice:

- Trace one eval case from dataset to runner to metrics.
- Explain task success, tool-call correctness, policy compliance, pass^k, and
  confidence intervals.
- Connect trace logs to debugging and regression gates.

Deliverable:

- An engineering-readiness map: eval, observability, recovery, deployment, and
  operational runbook.

## Chapter 09: Prompt 工程

Handbook pages: 204-232

Learning question: RetailCare 的 prompt 如何约束工具使用、政策合规、澄清问题和
注入防御?

RetailCare anchors:

- `src/retailcare/graph/prompts.py`
- `src/retailcare/graph/guardrails.py`
- `src/retailcare/tools/schema.py`
- `BUSINESS_RULES.md`
- `tests/test_hitl.py`
- `tests/test_faults.py`
- `eval/regression.py`

Practice:

- Compare `SYSTEM_L0` and `SYSTEM_RAG`.
- Identify every prompt rule that is also enforced in code.
- Explain prompt injection defense as layered defense: prompt instruction,
  tool schema, guardrails, policy checks, HITL, trace, regression tests.

Deliverable:

- A prompt safety review: prompt rule, code enforcement, test/eval evidence,
  remaining risk.

## Job-Readiness Pass

Handbook pages: 233-405

Learning question: 如何把 RetailCare 讲成一个真实、可信、能通过面试追问的 AI Agent
项目?

RetailCare anchors:

- `README.md`
- `ARCHITECTURE.md`
- `OPERATIONS_MANUAL.md`
- `reports/`
- `RetailCare_Orchestrator_项目定义_v1.md`
- `简历项目经历_RetailCare_Orchestrator.md`

Practice:

- Produce a 60-second project introduction.
- Prepare STAR answers for architecture, RAG, tool calling, memory, eval,
  safety, observability, and failure recovery.
- Rewrite resume bullets using only verifiable project behavior and metrics.

Deliverable:

- Interview package: project intro, STAR answer bank, resume bullets, and likely
  follow-up questions.

## Current Next Step

Start with Chapter 01: AI Agent 基础概念.

The first session should answer:

```text
根据资料第 10-25 页，RetailCare 为什么是一个 AI Agent 系统?
请把 LLM、Planning、Memory、Tools、闭环反馈分别对应到项目代码。
```
