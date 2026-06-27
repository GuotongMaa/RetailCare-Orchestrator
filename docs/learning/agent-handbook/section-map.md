# Handbook Section Map For RetailCare

This map follows the handbook directly. The active plan is the 9 handbook
chapters plus the job-readiness material, all tied to RetailCare code.

## PDF Sections

| PDF pages | Handbook section | RetailCare focus |
|---:|---|---|
| 1-2 | 封面与总目录 | Source metadata and page numbering |
| 3-6 | AI Agent 面试全攻略 | Overall study method: handbook theory plus project practice |
| 7-9 | AI Agent 面试八股文总目录 | Navigation for the 9 core chapters |
| 10-25 | 01 AI Agent 基础概念 | Agent definition, closed-loop task completion, project-wide architecture |
| 26-53 | 02 核心框架 | LangGraph/ReAct loop, state graph, routing, stop conditions |
| 54-84 | 03 RAG 技术 | Policy retrieval, chunks, Chroma fallback, citations, RAG evaluation |
| 85-110 | 04 工具调用 | Tool schemas, registry, dispatch, MCP, recovery, idempotency |
| 111-133 | 05 记忆系统 | Checkpoints, thread ids, trace-derived summaries, resumability |
| 134-155 | 06 多智能体系统 | When to split agents, handoff boundaries, ablation evidence |
| 156-177 | 07 大模型基础 | Model configuration, usage accounting, context/cost/safety tradeoffs |
| 178-203 | 08 工程化实践 | Evals, traces, regression gates, API, deployment, operations |
| 204-232 | 09 Prompt 工程 | System prompts, RAG prompt, policy constraints, injection defense |
| 233-246 | 2026 年 AI Agent 企业招聘需求分析 | Skills matrix and job-positioning check |
| 247-262 | 开源项目学习笔记 | Architecture comparison and project inspiration |
| 263-279 | AI Agent 项目简历撰写指南 | Resume bullets for RetailCare |
| 280-299 | STAR 面试稿准备指南 | STAR stories for RetailCare implementation decisions |
| 300-405 | 企业级 AI Agent 项目面试问答集 | Architecture defense and follow-up question practice |

## Core Study Bridge

| Handbook chapter | RetailCare code/practice bridge |
|---|---|
| AI Agent 基础概念 | Map `LLM + Planning + Memory + Tools` to `graph/`, `runtime.py`, `memory/`, and `tools/`. |
| 核心框架 | Explain the LangGraph ReAct loop in `src/retailcare/graph/agent.py`. |
| RAG 技术 | Trace `search_policy` through `policy/store.py`, `policy/rag.py`, and tool results. |
| 工具调用 | Build the 8-tool contract matrix from `tools/schema.py`, `registry.py`, `impl.py`, and MCP. |
| 记忆系统 | Explain checkpointed state, `thread_id`, resume, trace, and ticket summary. |
| 多智能体系统 | Use ablation/eval reports to decide whether specialist agents are justified. |
| 大模型基础 | Tie model settings, token usage, cost, and hallucination risk to config and guardrails. |
| 工程化实践 | Connect eval datasets, metrics, traces, regression gates, API, Docker, and runbooks. |
| Prompt 工程 | Compare prompt instructions with code-level enforcement and tests. |

## Citation Pattern

When answering future project questions:

```text
资料依据:
- 资料第 X 页: ...
- 资料第 Y 页: ...

项目对应:
- `path/to/file.py`: ...

我的理解:
- ...
```
