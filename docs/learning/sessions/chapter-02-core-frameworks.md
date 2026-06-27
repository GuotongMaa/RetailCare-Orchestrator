# 第 2 章：核心框架

日期：2026-06-21

## 资料页码

- 资料第 26 页：本章主线是 ReAct、Plan-and-Execute、Reflexion、LangGraph 和多 Agent 框架。
- 资料第 27-29 页：ReAct 的核心是推理、行动、观察交替，Observation 必须来自真实工具或环境。
- 资料第 33 页：ReAct 的局限包括多轮调用成本高、格式脆弱、复杂任务上可能缺少全局规划。
- 资料第 35、37 页：Plan-and-Execute 适合步骤多、结构清晰、需要全局分解的任务；ReAct 更适合动态工具交互。
- 资料第 38-39 页：Reflexion 把评估和反思显式化，形成可复用的策略记忆。
- 资料第 45-47 页：LangGraph 把 Agent 工作流表示成图，节点是处理步骤，边是流转关系，适合条件路由、回环修复、人机协同和复杂业务流程。
- 资料第 51-53 页：核心面试点包括 Observation 不能由模型伪造、停止条件、ReAct vs Plan-and-Execute 如何选。

## 本章目标

理解 RetailCare 为什么采用：

```text
单 Agent + ReAct 式循环 + LangGraph 状态机 + 工具护栏
```

而不是：

```text
先完整规划再执行 / Plan-and-Execute
多 Agent 分工 / Multi-Agent
完整 Reflexion 自反思框架 / Reflexion
```

## 知识点卡片 1：ReAct

知识点：ReAct 框架

中英对照：推理-行动 / ReAct, Reasoning + Acting；观察 / Observation

资料依据：资料第 27-29 页、第 33 页。

资料原意：ReAct 把“想”和“做”交替起来。模型不是一次性给最终答案，而是每一步先决定行动，再接收工具返回的 Observation，再继续判断。Observation 必须来自工具或环境，不能由模型自己编造。

RetailCare 例子：退货退款流程天然适合 ReAct。用户说“我要退这件衣服”，系统不能直接生成答案，而是要先查订单、判断商品、检查政策、确认金额，再决定创建退货、拒绝、澄清或升级人工。

具体场景：

```text
用户: 我想退 O1001 里的 I1，尺码不合适
Agent: 判断需要查退货资格
Tool: check_return_eligibility 返回 eligible=true, refund_amount=29
Agent: 判断是低价值可退货，但写操作需要确认
System: HITL interrupt
用户: yes
Tool: create_return_request
Agent: 返回 ticket id 和退款说明
```

项目证据：

- `src/retailcare/graph/agent.py` 明确写着 `agent_node -> tools_node -> agent_node`。
- `_route()` 根据最后一条消息是否有 `tool_calls` 决定继续到 tools 还是 END。
- `tools_node()` 把工具结果变成 tool message，作为下一轮模型决策的 Observation。
- `reports/demo_transcript.md` 展示了低价值退货先 HITL 确认，再创建退货单。

为什么这样设计：售后任务路径不长，但分支很多。用户信息可能缺失，工具结果可能改变下一步，比如高价值退款要升级人工，低价值退款要确认，非退货商品要阻断。ReAct 的逐步观察很适合这种动态分支。

替代方案：Plan-and-Execute。

为什么暂时不选替代方案：当前 RetailCare 的主任务不是长链路规划，而是短链路、高风险、多分支的售后动作。先生成完整计划容易被工具结果打断，而且会增加模型调用和计划维护成本。

局限与后续扩展：ReAct 可能短视，复杂投诉、多部门协作、跨系统补偿审批这类长任务，未来可能需要 Planner 或子图。

面试表达：RetailCare 选择 ReAct 不是因为它更炫，而是因为售后场景需要根据工具返回动态分支。每一步都要等订单、政策、资格判断等真实 Observation，尤其写操作还要经过护栏和人工确认，所以逐步“观察-行动”的 ReAct 比一次性计划更贴合。

## 知识点卡片 2：Plan-and-Execute

知识点：Plan-and-Execute 框架

中英对照：规划-执行 / Plan-and-Execute；重规划 / Re-planning

资料依据：资料第 35、37、52-53 页。

资料原意：Plan-and-Execute 先制定完整计划，再分步执行。它适合步骤多、结构清晰、需要全局分解的任务，例如多文件代码修改、复杂调研、数据分析流水线。它的风险是计划一开始错了，会影响后续全局，需要重规划机制。

RetailCare 例子：RetailCare 当前没有使用显式 Planner 先输出完整 DAG。它更像每一步即时决策。

具体场景：退货流程看似可以写成计划：

```text
1. 查订单
2. 查政策
3. 判断资格
4. 创建退货或升级人工
```

但实际中用户可能没有给 item_id，商品可能不可退，退款金额可能高于阈值，用户可能拒绝确认。每一步都会改变后续路径，所以完整前置计划收益有限。

项目证据：

- `ARCHITECTURE.md` 明确说当前是 single ReAct agent。
- `src/retailcare/graph/agent.py` 只有 agent/tool 两类节点，没有 planner/executor 两阶段节点。
- `reports/ablation_report.md` 说明 L0 到 L1 的收益来自 guardrails/HITL/RAG 等硬化，不是来自引入 Planner。

为什么这样设计：RetailCare 的核心可靠性问题不是“不会拆复杂计划”，而是“是否能在高风险写操作前做正确判断”。因此先加强工具、护栏、评测和恢复，比引入 Planner 更直接。

替代方案：引入 Planner 节点，先生成售后处理计划，再由 Executor 执行。

为什么暂时不选替代方案：对当前退款主流程，Planner 可能增加延迟和成本，还可能生成看似完整但被后续工具结果推翻的计划。

局限与后续扩展：如果后续加入“投诉升级 + 多部门审批 + 补偿方案 + 物流追踪 + 复盘报告”的长流程，可以考虑 Plan-and-Execute 或 LangGraph 子图。

面试表达：我会把 Plan-and-Execute 作为未来复杂工单的扩展方向，而不是当前第一选择。当前项目先用 ReAct 处理动态工具反馈，用评测数据决定是否需要更复杂拓扑。

## 知识点卡片 3：LangGraph

知识点：LangGraph 状态机

中英对照：状态图 / StateGraph；节点 / Node；边 / Edge；检查点 / Checkpoint；中断 / Interrupt

资料依据：资料第 45-47 页。

资料原意：LangGraph 把 Agent 工作流画成图。节点是处理步骤，边是流转关系。相比普通 AgentExecutor，LangGraph 更适合条件路由、循环、人工审核、回环修复和复杂业务流程。

RetailCare 例子：RetailCare 用 LangGraph 表达一个最小但生产可用的图：

```text
START -> agent_node -> tools_node -> agent_node -> END
```

具体场景：当模型调用写工具 `create_return_request` 时，`tools_node` 不是直接执行，而是先进入 guardrail；低价值退款触发 `interrupt()`，等待用户确认；确认后通过 checkpoint 恢复执行。

项目证据：

- `build_agent()` 创建 `StateGraph(AgentState)`。
- 图里有 `agent` 和 `tools` 两个节点。
- `add_conditional_edges()` 用 `_route()` 判断去 tools 还是 END。
- runtime 用 `SqliteSaver` 作为 checkpointer，并用 `thread_id` 支持跨会话恢复。
- `tests/test_hitl.py` 验证 interrupt 后未确认不写入，确认后才执行。
- `tests/test_memory.py` 验证 trace 能生成 ticket summary。

为什么这样设计：LangGraph 让“循环、暂停、恢复、人工确认”变成显式结构，而不是散落在普通 Python if/else 或一次性链路里。这对售后退款这种需要可恢复和可审计的场景很重要。

替代方案：直接用普通 LangChain AgentExecutor 或手写 while loop。

为什么暂时不选替代方案：普通 AgentExecutor 对 HITL、checkpoint 和条件恢复支持不如状态图清晰；手写 loop 可控但后续扩展人工节点、子图、评测插桩会更乱。

局限与后续扩展：当前图很小，只有 agent/tools 两类节点。未来可以扩展出 refund 子图、complaint 子图、review 节点或 planner 节点。

面试表达：RetailCare 用 LangGraph 不是为了堆框架，而是因为售后场景需要暂停、恢复、条件分支和审计。即使当前图很克制，也为后续复杂流程留出了结构化扩展点。

## 知识点卡片 4：Reflexion

知识点：Reflexion 框架

中英对照：反思 / Reflection；评估器 / Evaluator；反思器 / Reflector；策略记忆 / Strategy Memory

资料依据：资料第 38-39 页。

资料原意：Reflexion 不只是“让模型检查一遍”，而是把评估、反思和重试显式化，把失败教训变成可复用的策略记忆。

RetailCare 例子：RetailCare 没有完整 Reflexion 框架，但有工程化的弱反思机制。

具体场景：工具调用失败时，错误会作为 tool error 返回，模型可以修正参数或升级人工；离线评测时，error taxonomy 会统计 tool_selection_error、missing_param_no_clarify 等失败类型，指导下一轮改进。

项目证据：

- `tools_node()` 会把工具错误写回消息。
- `tools/recovery.py` 负责 bounded retry 和降级恢复。
- `trace/logger.py` 记录 tool_error、decision、interrupt。
- `reports/error_taxonomy.md` 和 `reports/ablation_report.md` 用于离线复盘。

为什么这样设计：高风险售后场景里，在线“自我反思”不能替代确定性的业务规则。项目优先把反思落到工具错误、trace、eval 和报告上。

替代方案：引入 Actor/Evaluator/Reflector 三段式 Reflexion。

为什么暂时不选替代方案：会增加额外模型调用、延迟和不确定性；当前更需要确定性 guardrail 和回归评测。

局限与后续扩展：未来可以在 eval 后自动生成失败案例总结，或对固定错误类型生成 prompt/tool schema 改进建议。

面试表达：RetailCare 没有把 Reflexion 作为在线主链路，而是把反思工程化为 trace 和 eval。这样更适合生产售后，因为我们更关注可审计和可回归，而不是让模型自由自省。

## 知识点卡片 5：单 Agent vs 多 Agent

知识点：单 Agent 多工具 vs 多 Agent 协作

中英对照：单智能体 / Single Agent；多智能体 / Multi-Agent；子图 / Subgraph

资料依据：资料第 26 页提到多 Agent 框架，第 53 页给出对比速记；第 1 章第 23 页也提到单 Agent 多工具实现简单、延迟低，多 Agent 有分工但协调成本高。

资料原意：框架选择取决于任务结构、边界、延迟、成本和协调复杂度，不是 Agent 越多越高级。

RetailCare 例子：RetailCare 当前明确选择单 ReAct agent + 8 个工具，而不是退款 Agent、物流 Agent、优惠券 Agent、投诉 Agent 全拆开。

具体场景：用户的售后意图经常会从“查订单”转到“我要退款”再转到“能不能补偿”。单 Agent 能在一个上下文里直接切换工具；多 Agent 会引入路由、上下文传递和一致性问题。

项目证据：

- `ARCHITECTURE.md` 写明“why one agent, not seven”。
- L0/L1/L2 拓扑设计中，L2 refund subgraph 只作为未来工作。
- `reports/ablation_report.md` 显示 L0 到 L1 不加新 Agent，pass@1 从 0.633 到 0.80，tool-selection errors 从 11 到 6。

为什么这样设计：项目先把可靠性问题用 guardrails、RAG、HITL、idempotency、eval 解决。数据已经显示“硬化单 Agent”能显著改善结果，所以没有必要过早拆多 Agent。

替代方案：多 Agent 分工，比如 refund agent、shipping agent、coupon agent、complaint agent。

为什么暂时不选替代方案：当前任务边界清楚，工具数量可控；多 Agent 会带来协调成本、延迟、状态同步和责任归因问题。

局限与后续扩展：如果错误分析显示退款逻辑长期混淆，或者投诉处理变成长流程，可以拆 refund subgraph 或 complaint subgraph。

面试表达：我不会为了“多 Agent”而多 Agent。RetailCare 的设计原则是用 eval 决定拓扑。当前数据说明加强单 Agent 的护栏和工具正确性已经有效，所以先 harden，再 split。

## 本章总图

```text
用户请求
  |
  v
Conversation runtime
  |
  v
LangGraph StateGraph
  |
  v
agent_node: LLM 根据上下文决定是否调用工具
  |
  | tool_calls
  v
tools_node: guardrails / HITL / recovery / tool execution
  |
  | tool result = Observation
  v
agent_node: 根据 Observation 再决策
  |
  | 无 tool_calls 或达到 MAX_STEPS
  v
END
```

## 验证

本节运行：

```bash
.venv/bin/python -m pytest tests/test_memory.py tests/test_hitl.py -q
```

结果：11 passed。

这组测试证明：

- HITL interrupt 后，确认前不会执行写操作。
- 用户确认后才创建退货单。
- 用户拒绝时不会写入。
- trace 中会记录确认决策。
- trace 可以生成 ticket summary。

## 面试总表达

RetailCare 的核心框架是单 Agent 的 ReAct 式 LangGraph。资料里 ReAct 的优势是每一步都基于真实 Observation 再决策，这非常适合电商售后：用户信息可能不完整，工具结果会改变分支，高风险退款必须先校验再确认。项目没有一开始用 Plan-and-Execute，是因为当前退款主流程不是长规划任务，而是短链路、多分支、高风险动作；完整前置计划反而可能增加成本和被工具结果推翻。项目也没有一开始拆多 Agent，因为 ablation 数据显示，在不增加 Agent 的情况下，加入 guardrails、HITL 和 RAG 已经把 pass@1 从 0.633 提升到 0.80/0.833。我的设计原则是：先把单 Agent 做可靠、可评测、可恢复，再用数据决定是否拆子图或多 Agent。

## 下一章连接

第 3 章进入 RAG 技术。RetailCare 里可以重点讲：

- 为什么政策知识适合 RAG；
- policy prompt 和 policy RAG 的差异；
- 版本化政策 chunk 如何支持审计；
- 为什么资料里的“RAG 不等于 Agent”在 RetailCare 中要和工具/护栏/评测结合起来理解。
