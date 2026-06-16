# RetailCare Orchestrator — 项目定义(敲定版 v1)

> 本文是逐项敲定后的**项目定义/开工依据**。区别于 `设计v2.md`(评估与方案探讨),本文是"我们确定要做的系统、以及怎么做"。

---

## 1. 定位与真实故事

**做什么**:一个**售后场景的电商客服助手**,处理订单查询、物流、退货退款、优惠券/补偿、投诉升级 5 类多轮任务,并用严谨评测证明它**可靠、合规、不越权**。

**真实故事(一句话)**:电商退款是会赔真金白银的高风险多轮操作——本项目做一个能**可靠完成**它、且能**证明它不越权违规**的 Agent 系统。

**双轮目标**:产品闭环(能跑、有前端、可调用)+ 严谨评测(benchmark、指标、消融)。

---

## 2. 已敲定决策一览(请先核对这张表)

| 维度 | 敲定结论 |
|---|---|
| 业务范围 | 5 类:订单查询、物流查询、**退货退款(hero)**、优惠券/补偿、投诉升级 |
| 多模态 | **暂缓**,预留图片输入接口,到退货模块再定 |
| 项目重心 | 产品闭环 + 严谨评测(双轮) |
| Agent 架构 | **单 Agent 起步 + 工具路由**,后做多 Agent 对比实验 |
| 框架 | **LangGraph**(状态图 + checkpoint + interrupt HITL) |
| 模型 | **LiteLLM 兼容层**,多模型可切(DeepSeek/Qwen/GPT/Claude) |
| 语言 | **英文为主** |
| 数据 · 对话层 | **Bitext** retail-ecommerce + customer-support |
| 数据 · 工具层 | **BFCL v4**(function-calling 评测) |
| 数据 · 任务评测层 | **自建标注退款任务**(τ³ 范式)+ τ³-bench retail 打底 |
| 退款风控 | 低额确认执行 / 高额·异常人工升级 / **幂等 + 审计** |
| 记忆 | 短期对话 + **工单状态摘要**(长期画像作消融) |
| 政策接入 | **RAG 检索 + 高风险前强制 policy check** |
| 交付 | FastAPI 服务 + **轻量 Web 前端**(可视化对话+trace)+ CLI 评测 |

---

## 3. 业务范围与闭环

5 类任务按"风险 × 频率"分层处理(不是均摊投入):

| 意图 | 类型 | 处理方式 |
|---|---|---|
| 订单查询 | 只读·高频 | 工具直查,低延迟 |
| 物流查询 | 只读·高频 | 工具直查,低延迟 |
| **退货退款** | **写·高风险** | **走完整风控闭环(hero,见 §6)** |
| 优惠券/补偿 | 解释只读 / 发放写 | 解释直答;发放走风控闭环 |
| 投诉升级 | 出口 | 够格则 `escalate_to_human`,不滥用 |

**通用流程**:接入 → 意图识别 → 只读类直接查询作答 / 写操作类进入风控闭环 → 信息缺失则澄清 → 政策 check → 用户确认或人工升级 → 幂等执行 → 回执 → 记 trace。

---

## 4. 系统架构(v1 = 单 Agent 形态)

```
用户 ──> 主 Agent(LangGraph 状态图, ReAct)
            │  意图识别 + 工具路由 + 多轮管理
            ├─ 只读工具:get_order / get_shipment / search_policy / get_coupon / check_return_eligibility
            ├─ 政策 RAG 组件(检索 + 版本化引用)
            ├─ 风控/Guardrail 校验器(写操作前:参数完整性 + policy check + 幂等键)
            ├─ HITL 中断点(interrupt():等用户确认 / 人工)
            ├─ 写操作工具:create_return_request / issue_compensation
            └─ 升级出口:escalate_to_human
         记忆:短期 state + 工单摘要(checkpointer 持久化)
         Trace:每次工具调用 / 中断 / 失败原因落盘(JSON)
```

**演进**:v1 单 Agent 跑通后,把退款拆成带专属工具子集 + 专属 guardrail 的独立子图,做单 vs 多 Agent 对比(见 §10 E1)。多模态预留:工具与输入层保留图片字段,退货模块决定是否接 VLM 质检。

---

## 5. 工具层(契约 + 风险分级)

```python
# 只读(低风险,可自动执行)
get_order(order_id) -> Order
get_shipment(order_id) -> Shipment
search_policy(query) -> list[PolicyChunk]            # 带 version
get_coupon(user_id) -> list[Coupon]
check_return_eligibility(order_id, item_id, reason) -> Eligibility

# 写操作(高风险:校验 + policy check + 确认/升级 + 幂等 + 审计)
create_return_request(order_id, item_id, reason, idempotency_key) -> Ticket
issue_compensation(user_id, reason, amount, idempotency_key) -> Result
escalate_to_human(user_id, reason, transcript) -> Handoff
```

- 每个工具用 **Pydantic** 定义 I/O schema;写操作强制 `idempotency_key`。
- 工具层**通过 MCP 暴露**(契约标准化、可复用),独立于 Agent,可单测。

---

## 6. 退款核心闭环(hero · 状态机)

```
收到退款诉求
  → 取订单&商品(只读)
  → 检索退款政策(RAG, 带版本)
  → 资格判断(规则 + 政策 check)
  → [信息缺失] → 向用户澄清(回到资格判断)
  → [合规 且 金额 < 阈值] → 用户确认 → 幂等执行 create_return_request → 回执
  → [金额 ≥ 阈值 / 异常 / 政策冲突] → escalate_to_human(带完整 transcript)
  → 全程写 trace
```

**关键工程点**:
- **幂等键 = (order_id, item_id)**:重试或重复点击都不二次退款。
- **HITL = LangGraph `interrupt()`**:高风险节点中断,确认/人工后从 checkpoint 恢复。
- **政策版本化**:RAG 命中的政策片段带版本号写进 trace,可复盘"依据哪版规则"。
- **故障恢复**:工具 timeout/报错/过期数据 → 重试 → 兜底话术 → 升级(并做故障注入测试)。

---

## 7. 记忆与状态

- **短期**:LangGraph state 内最近对话 + 用户刚确认的信息(多轮连续性)。
- **工单摘要**:如"已确认订单 X,原因=尺码不合适,待确认退款金额"(控成本/防遗忘)。
- **长期画像**:默认**不开**,作为消融项(§10 E5)验证其对售后的边际价值。
- 用 **checkpointer** 持久化,支持会话恢复。

---

## 8. 数据方案(三层 · 英文)

**核心认知:没有单一现成数据集能同时给"真实对话 + 工具调用标准答案",分三层各取所需。**

| 层 | 数据 | 用途 | 备注 |
|---|---|---|---|
| 对话真实性 | Bitext retail-ecommerce + customer-support | 意图分类、话术、用户模拟器、RAG FAQ 语料 | 英文、CDLA 许可可商用;**单轮、无工具标注** |
| 工具调用评测 | BFCL v4 | 工具选择 / 参数正确率(含 multi-turn) | 带标准答案的 function-call 任务 |
| 任务级评测 | **自建退款任务**(30–50 条,标 `evaluation_criteria.actions`)+ τ³-bench retail 打底 | 任务成功率 / 政策合规 / pass^k | **自建标注=核心工作量,也是亮点** |

> 评测标签(任务成功/合规)必须自建,因为对话数据不含工具与动作标注。这正是"严谨评测"重心的工作所在。

---

## 9. 评测体系

**指标**:`task_success_rate`、**`pass^k`(一致性,核心)**、`tool_call_accuracy`、`argument_accuracy`、`policy_violation_rate`、`unnecessary_handoff_rate`、`human_escalation_precision`、`clarification_quality`、`avg_turns_to_resolution`、`latency_p95`、`cost_per_task`。

**严谨性**:任务量小 → 多 seed + 多次运行 + 置信区间;核心结论用 pass^k 而非单次 pass@1。

**错误分类学**:意图路由错 / 工具选择错 / 参数缺失未澄清 / 工具顺序错 / 违反政策 / 过早升级 / 长上下文遗忘 / 答复与工具结果不一致。LLM-as-judge 初筛 + 人工抽检校准。

**已知局限**:LLM 模拟用户不是人类用户的可靠代理 → 用人工抽检校准缓解。

**Eval 回归 CI**:每次 PR 自动跑小规模 eval,基线回归即拦截。

---

## 10. 实验与消融

| 实验 | 问题 | 主指标 |
|---|---|---|
| **E1(主)** | 单 Agent vs 多 Agent(拆退款子图)值不值 | pass^k、违规率、p95、cost |
| E2 | 路由:LLM 全权 / 规则优先 / +置信度阈值 | 路由准确率、恢复率、成本 |
| E3 | 政策:写进 prompt vs RAG vs 高风险前强制 check | 违规率、引用准确率、延迟 |
| E4 | 高风险工具:直接执行 vs 确认 vs 人工升级 | 误操作率、解决率、轮次 |
| E5 | 记忆:短期 / +摘要 / +长期画像 | 长任务成功率、重复提问率、token |
| E6 | 强/弱模型混合(LiteLLM) | **质量 × 成本 Pareto 前沿** |

---

## 11. 技术栈

Python · **LangGraph**(状态图/checkpoint/interrupt)· **LiteLLM**(多模型)· **FastAPI** + **轻量 Web 前端**(可视化对话与 trace)· **FAISS/Chroma**(政策 RAG)· **Pydantic**(工具契约)· **MCP**(工具暴露)· pytest + **eval 回归 CI** · Docker · LangSmith/Phoenix(可观测)· SQLite/Postgres(订单/工单 mock 数据)。

---

## 12. 交付物与里程碑

**交付物**:`README.md`、`ARCHITECTURE.md`、`BUSINESS_RULES.md`、`tools/schema.py`、`graph/`(LangGraph 状态图)、`eval/`(BFCL + 自建退款 runner + 指标)、`web/`(前端)、`reports/ablation_report.md`、`reports/error_taxonomy.md`、Demo。

**里程碑(建议 4 阶段)**:

1. **W1–2 基线**:工具层 + mock 数据 + 单 Agent + Bitext 接入 + trace 日志。
2. **W3–4 退款闭环**:风控(确认/幂等/HITL)+ 政策 RAG + 故障注入 + 自建退款评测集 + BFCL 接入。
3. **W5–6 评测与消融**:指标体系 + 错误分类 + E1/E3/E4 + eval CI。
4. **W7 收尾**:轻量 Web 前端 + E2/E5/E6 选做 + README/ARCHITECTURE + Demo。

---

## 13. 明确不做(v1 边界)

不接真实支付/退款接口 · 不做全量电商能力 · 不做复杂权限系统 · v1 不做多模态(仅预留接口)· 不主打模型训练(trace→数据→轻量训练作为后续可选演进)。

---

*开工锚点:先把"单 Agent + 工具层 + 退款风控闭环 + trace"在英文 mock 环境跑通,再叠评测与消融。*
