# Learning and Engineering Decisions

## 2026-06-19: Use File-Backed Learning Memory

Decision: keep cross-conversation learning state in `docs/learning/` instead of
depending on chat history.

Reason: the project will be studied across many conversations. Files are
searchable, versionable, and easy for a new conversation to read before
continuing.

## 2026-06-19: Learn by Project Anchors, Not Abstract Topics Alone

Decision: every roadmap module maps to specific RetailCare files and a concrete
deliverable.

Reason: agent engineering terms become useful only when tied to runnable code,
tests, traces, and business constraints.

## 2026-06-19: Preserve Existing Project Logic During Kickoff

Decision: kickoff only adds learning documentation; no business code is changed.

Reason: first establish a stable mental model and a continuation protocol before
optimizing implementation.

## 2026-06-19: Treat Single-Agent as the Baseline

Decision: study and improve the current single-agent architecture before adding
multi-agent orchestration.

Reason: `ARCHITECTURE.md` and reports show the project intentionally hardens a
single ReAct agent first, then uses eval data to decide whether splitting is
worth the complexity.

## 2026-06-19: Keep Learning Code Fully Isolated

Decision: all learning exercises, scratch scripts, prototypes, and experimental
notebooks live under `learning_lab/` by default.

Reason: the main RetailCare architecture should remain stable and understandable.
Learning should be safe to explore without mixing temporary code, dependencies,
or partial ideas into production-facing modules.

Promotion rule: a learning experiment can move into `src/`, `eval/`, `tests/`,
or `web/` only after it has a clear value statement, impact assessment, tests or
eval coverage, and a rollback plan.

## 2026-06-21: Use The AI Agent Handbook As Page-Aware RAG

Decision: extract `海云大模型AIAgent应用面试通关手册.pdf` into
`docs/learning/agent-handbook/pages.jsonl` and search it before answering
handbook-backed AI Agent learning, interview, or architecture questions.

Reason: the user wants RetailCare study to combine runnable project practice
with the new 9-part AI Agent learning material. Page-aware retrieval lets future
answers cite the source precisely instead of relying on memory or vague summary.

## 2026-06-21: Adopt The Handbook-Code Chapter Sequence

Decision: use the handbook chapter sequence as the active learning plan: AI
Agent 基础概念, 核心框架, RAG 技术, 工具调用, 记忆系统, 多智能体系统, 大模型基础,
工程化实践, and Prompt 工程, followed by a job-readiness pass.

Reason: the user has already skimmed the handbook and now wants full project
cognition by connecting each handbook chapter to RetailCare's architecture and
implementation code.

## 2026-06-21: Use Project-Proof Knowledge Cards

Decision: every future chapter note should use a reusable project-proof template:
handbook knowledge point -> RetailCare proof example -> concrete scenario ->
design reason -> alternative/tradeoff -> limitation -> interview expression.

Reason: the user does not want abstract handbook summaries or code-only notes.
The goal is to turn each handbook idea into a concrete RetailCare example that
can survive interview follow-up questions. For example, Chapter 02 should not
only define ReAct and Plan-and-Execute; it should explain why RetailCare chose a
ReAct-style loop for refund/customer-service tasks and when Plan-and-Execute
would become a better fit.

## 2026-06-27: Adopt The State-Grounded ReAct Doctrine

Decision: treat RetailCare as a ReAct-first, LangGraph State-governed,
system-enforced safety architecture.

Reason: the project should not force after-sales work into rigid workflows.
Real customer-service conversations can switch between order status, shipment,
refunds, coupons, compensation, different items, different orders, and complaints.
ReAct provides the dynamic behavior needed for that agentic experience, while
LangGraph state provides continuity, checkpointing, interrupt/resume, and recovery
so the agent does not lose track in long or branching conversations.

Safety rule: every model tool call is only a proposal to the system. The backend
retains final authority through typed schemas, ownership checks, business rules,
policy checks, guardrails, HITL confirmation, idempotency, and audit. High-risk
write operations must be checked before execution.

Engineering implication: future upgrades should first strengthen the state schema,
business-state grounding, recovery points, and guardrail integration. Additional
nodes, subgraphs, or specialist agents are acceptable only when they make state,
safety, evaluation, or maintainability better; they are not the default goal.
