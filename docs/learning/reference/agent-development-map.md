# Agent Development Map

本文件是 Agent 发展历史与知识分类的宏观地图，仅作为参考资料保存。

它不计入 RetailCare 12 阶段正式学习进度。

## 总体演进

```text
大模型基础
  -> RAG / 检索增强
  -> CoT / Planning / Program-aided Reasoning
  -> Tool Calling / Function Calling
  -> ReAct: Reason + Act 循环
  -> Workflow / Graph / State / Memory
  -> Guardrails / HITL / Recovery
  -> Harness / Eval / Observability
  -> SDK / MCP / Coding Agent / Production Agent
```

## 可视化总地图

```mermaid
flowchart TD
  A["大模型基础<br/>LLM / Chat Model"] --> B["外部知识<br/>RAG / WebGPT"]
  B --> C["推理范式<br/>CoT / Planning / PAL"]
  C --> D["工具使用<br/>Tool Calling / MRKL / ReAct"]
  D --> E["工程化 Agent<br/>State / Memory / Workflow / HITL"]
  E --> F["生产级系统<br/>Eval / Trace / Guardrails / Recovery"]
  F --> G["现代生态<br/>SDK / Framework / MCP / Coding Agents"]

  subgraph S1["一、思想 / 方法论"]
    RAG["RAG<br/>外部知识增强"]
    COT["CoT<br/>分步骤推理"]
    PLAN["Planning<br/>先规划再执行"]
    PAL["PAL<br/>让模型写程序，运行时负责计算"]
    MRKL["MRKL<br/>模型 + 工具模块"]
    REACT["ReAct<br/>Reason + Act + Observe"]
    REFLECT["Reflexion / Self-Refine<br/>失败后反思修正"]
    WORKFLOW_THINK["Workflow 思维<br/>确定流程优先于盲目自主"]
  end

  subgraph S2["二、核心工程能力"]
    TOOL["Tool Calling<br/>结构化调用外部函数"]
    STATE["State<br/>保存任务状态"]
    MEMORY["Memory<br/>短期 / 长期 / 摘要记忆"]
    HITL["HITL<br/>人工确认与审批"]
    GUARD["Guardrails<br/>权限、规则、合规约束"]
    RECOVERY["Recovery<br/>失败重试、恢复、降级"]
    TRACE["Observability<br/>Trace / Log / Cost / Latency"]
    HARNESS["Eval Harness<br/>任务集、评分、回归测试"]
  end

  subgraph S3["三、框架 / SDK / 平台"]
    LANGCHAIN["LangChain<br/>LLM 应用组件生态"]
    LANGGRAPH["LangGraph<br/>状态图、可恢复 Agent 编排"]
    OPENAI_SDK["OpenAI Agents SDK<br/>工具、状态、审批、编排"]
    CREW["CrewAI / AutoGen<br/>多 Agent 编排框架"]
    CODEX["Codex / Claude Code<br/>代码工程 Agent"]
    LANGSMITH["LangSmith 等<br/>观测与调试平台"]
  end

  subgraph S4["四、协议 / 接口标准"]
    MCP["MCP<br/>模型连接工具与数据源的协议"]
    JSONSCHEMA["JSON Schema<br/>工具参数结构化"]
    OPENAPI["OpenAPI<br/>HTTP API 描述"]
    FUNCTIONCALL["Function / Tool Calling API<br/>模型与工具交互接口"]
    AGENTSMD["AGENTS.md / Skills<br/>给 Agent 的项目级操作说明"]
  end

  subgraph S5["五、评测标准 / Benchmark"]
    HELM["HELM<br/>模型综合评测"]
    OPENEVALS["OpenAI Evals<br/>自定义评测框架"]
    AGENTBENCH["AgentBench<br/>Agent 多环境评测"]
    SWEBENCH["SWE-bench<br/>真实代码任务评测"]
    TAUBENCH["tau-bench<br/>客服/零售工具交互评测"]
    PASSK["pass^k<br/>多次运行一致性指标"]
  end

  subgraph S6["六、历史参照 / 不建议作为主线"]
    AUTOGPT["早期 AutoGPT 式无限循环"]
    PLUGINS["旧 ChatGPT Plugins 形态"]
    RAWPROMPT["裸 Prompt 串联一切"]
    RAWTOOLS["无 Schema 的字符串工具调用"]
  end

  S1 --> S2
  S2 --> S3
  S2 --> S4
  S2 --> S5
  S6 -.提供历史经验.-> S1
```

## 分类理解

| 类别 | 解决什么问题 | 代表 |
|---|---|---|
| 思想 / 方法论 | 怎么设计 agent 的行为 | RAG、CoT、PAL、ReAct、Workflow、Reflection |
| 核心工程能力 | agent 系统必须具备什么能力 | Tool Calling、State、Memory、HITL、Guardrails、Eval、Trace |
| 框架 / SDK | 用什么工具实现这些能力 | LangGraph、LangChain、OpenAI Agents SDK、CrewAI、Codex、Claude Code |
| 协议 / 接口标准 | 模型如何连接外部世界 | MCP、JSON Schema、OpenAPI、Function Calling |
| 评测标准 | 怎么证明 agent 靠谱 | SWE-bench、tau-bench、AgentBench、pass^k、OpenAI Evals |
| 历史参照 | 了解即可，不建议主学 | 早期 AutoGPT、裸 prompt chain、旧 Plugins |

## 一句话记忆

```text
思想决定设计，工程能力决定可靠性，框架负责实现，协议负责连接，评测负责证明。
```

## 推荐搜索路线

1. `RAG tutorial for beginners`
2. `OpenAI function calling tutorial`
3. `ReAct agent explained`
4. `LangGraph tutorial state graph`
5. `LLM agent memory explained`
6. `human in the loop agents`
7. `LLM evals for agents`
8. `MCP model context protocol tutorial`
9. `Codex CLI or Claude Code agent workflow`

