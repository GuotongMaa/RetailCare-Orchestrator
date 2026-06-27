# Learning Progress

Last updated: 2026-06-21

## Current Status

Active plan: handbook-driven RetailCare learning.

Learning objective:

> Take each chapter of `海云大模型AIAgent应用面试通关手册.pdf` and connect it
> directly to RetailCare's architecture, implementation code, tests, traces,
> evals, and interview story.

The handbook has already been extracted into a page-aware local RAG corpus:

- `docs/learning/agent-handbook/pages.jsonl`
- `docs/learning/agent-handbook/metadata.json`
- `learning_lab/rag/search_agent_handbook.py`

Future answers should search this corpus first when the question is about AI
Agent concepts, RetailCare architecture, implementation choices, or interview
preparation, and should cite physical PDF page numbers.

## Active Chapter

Current chapter: Job-readiness pass.

Source range: handbook pages 233-405.

Main question:

```text
如何把 RetailCare 讲成一个真实、可信、能通过面试追问的 AI Agent 项目?
```

Code anchors for the next session:

- `README.md`
- `ARCHITECTURE.md`
- `OPERATIONS_MANUAL.md`
- `reports/`
- `docs/learning/sessions/`
- `RetailCare_Orchestrator_项目定义_v1.md`
- `简历项目经历_RetailCare_Orchestrator.md`

Expected output:

- Produce a 60-second project introduction.
- Prepare STAR answers for architecture, RAG, tool calling, memory, eval, safety, observability, and failure recovery.
- Rewrite resume bullets using only verifiable project behavior and metrics.
- Prepare likely follow-up questions and crisp answers.

## New Chapter Sequence

1. AI Agent 基础概念, pages 10-25.
2. 核心框架, pages 26-53.
3. RAG 技术, pages 54-84.
4. 工具调用, pages 85-110.
5. 记忆系统, pages 111-133.
6. 多智能体系统, pages 134-155.
7. 大模型基础, pages 156-177.
8. 工程化实践, pages 178-203.
9. Prompt 工程, pages 204-232.
10. Job-readiness pass, pages 233-405.

The full plan lives in `docs/learning/roadmap.md`.

## Session Workflow

For each chapter:

1. Search the handbook and cite useful pages.
2. Read the project files listed in `roadmap.md`.
3. Run or inspect the relevant tests, demo, trace, or eval code.
4. Produce a chapter note under `docs/learning/sessions/`.
5. Update this file with the completed chapter and next chapter.

## Recommended Next Prompt

```text
请开始 Job-readiness pass。检索资料第 233-405 页，并结合 RetailCare
的 README、ARCHITECTURE、OPERATIONS_MANUAL、reports 和前 9 章学习笔记，
整理 60 秒项目介绍、STAR 面试稿、常见追问答法和简历 bullet。
要求所有表达都能回指到项目证据，不要夸大。
```

## Completed Under The New Plan

- [x] Extracted the handbook into a page-aware local corpus.
- [x] Created the 9-chapter handbook-code plan.
- [x] Chapter 01: AI Agent 基础概念.
- [x] Chapter 02: 核心框架.
- [x] Chapter 03: RAG 技术.
- [x] Chapter 04: 工具调用.
- [x] Chapter 05: 记忆系统.
- [x] Chapter 06: 多智能体系统.
- [ ] Chapter 07: 大模型基础. (skipped/deferred by request)
- [x] Chapter 08: 工程化实践.
- [x] Chapter 09: Prompt 工程.
- [ ] Job-readiness pass.
