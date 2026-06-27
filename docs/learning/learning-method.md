# Learning Method

This file records the active RetailCare study method.

The reusable learning method is:

```text
handbook knowledge point -> RetailCare proof example -> concrete scenario
-> design reason -> tradeoff/alternative -> interview expression
```

The handbook provides the conceptual structure. RetailCare is the running
example. Code is important evidence, but it is not the only evidence. A good
learning note can also use architecture docs, business rules, eval reports,
traces, tests, demo transcripts, metrics, and resume material as proof.

## Core Principle

Do not study AI Agent concepts in isolation.

For every concept, answer five questions:

1. Where does the handbook explain it, and on which PDF pages?
2. What concrete RetailCare example can prove or illustrate it?
3. Why did RetailCare choose this design?
4. What alternative design does the handbook mention or imply, and why is it not
   the current best fit?
5. What limitation or future extension should be stated honestly?
6. How would I explain it in an interview without sounding like I only memorized
   definitions?

## Knowledge-Point Card Template

Use this card for each meaningful handbook knowledge point.

```text
知识点:
中英对照:
资料依据:
资料原意:
RetailCare 例子:
具体场景:
项目证据:
为什么这样设计:
替代方案:
为什么暂时不选替代方案:
局限与后续扩展:
面试表达:
```

Example for a future Chapter 02 topic:

```text
知识点: ReAct vs Plan-and-Execute
中英对照: 推理-行动 / ReAct; 规划-执行 / Plan-and-Execute
资料依据: 资料第 26-35 页
资料原意: ReAct 适合边观察边行动的动态工具任务; Plan-and-Execute 适合步骤清晰、需要全局分解的长任务。
RetailCare 例子: 退货退款场景中，用户信息可能不完整，工具结果可能触发不同分支，所以项目使用 ReAct 式循环。
具体场景: 用户说“我要退这个订单”，系统需要先查订单，再根据商品、金额、政策、用户确认决定下一步。
项目证据: `agent_node -> tools_node -> agent_node`, `MAX_STEPS`, guardrails, HITL, ablation report.
为什么这样设计: 售后任务路径短但分支多，ReAct 的逐步观察更适合; 先写完整计划反而容易被新工具结果打断。
替代方案: Plan-and-Execute。
为什么暂时不选替代方案: 当前主任务不是长规划，而是高风险、强校验、多分支的售后动作; 先规划完整 DAG 成本更高、收益不明显。
局限与后续扩展: 如果后续加入复杂投诉处理、跨系统补偿审批、多部门协作，可考虑 Planner 或子图。
面试表达: 我们选择 ReAct 不是因为它更“高级”，而是因为售后任务需要根据工具 observation 动态分支，同时写操作必须随时经过护栏。
```

## Session Template

Each formal learning session should produce one concrete note.

Use this structure:

```text
Chapter:
Handbook pages:
Chapter goal:
Key knowledge points:
Knowledge-point cards:
RetailCare architecture examples:
Concrete scenarios:
Why these designs:
Alternative designs and why not:
Project evidence:
Limitations and future extensions:
Interview version:
Open questions:
```

## Retrieval First

Before teaching or answering handbook-backed questions, search the local corpus:

```bash
python3 learning_lab/rag/search_agent_handbook.py "关键词" --top 5
```

Use physical PDF page numbers in answers, for example:

```text
资料第 11 页把 Agent 定义为结合规划、记忆与工具调用的闭环系统。
```

## Code Second

After retrieving the handbook evidence, immediately connect it to code.

Evidence can come from:

1. Source files under `src/retailcare/`.
2. Business rules and architecture docs.
3. Tests under `tests/`.
4. Eval datasets and metrics under `eval/`.
5. Reports, traces, API, deployment files, and resume materials.

## Learning Outputs

The target output is project cognition, not a pile of summaries.

After each chapter, the user should be able to:

- State the handbook knowledge points clearly, with Chinese and English terms.
- Give one or more concrete RetailCare examples for each important point.
- Explain why the project made this design choice.
- Compare the chosen design with plausible alternatives.
- Name the failure modes and safety controls.
- Answer likely interview follow-up questions with real project evidence.

## Chapter Order

Use the chapter sequence in `docs/learning/roadmap.md`:

1. AI Agent 基础概念.
2. 核心框架.
3. RAG 技术.
4. 工具调用.
5. 记忆系统.
6. 多智能体系统.
7. 大模型基础.
8. 工程化实践.
9. Prompt 工程.
10. Job-readiness pass.

## Boundaries

Learning notes and experiments live in `docs/learning/` and `learning_lab/`.

Production-facing code lives in:

- `src/retailcare/`
- `eval/`
- `tests/`
- `web/`

Only promote a learning experiment into production-facing code after it has a
clear value statement, tests or eval coverage, and a rollback plan.
