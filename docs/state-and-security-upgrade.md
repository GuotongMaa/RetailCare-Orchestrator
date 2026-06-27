# 系统升级设计:可信身份边界 + 结构化 State + 状态回灌

> 状态:草案 v1 · 2026-06-27
> 适用版本:当前 `dev` 分支(单 ReAct agent + LangGraph state + guardrail/HITL)
> 关联文档:[ARCHITECTURE.md](../ARCHITECTURE.md)

本文是一次架构升级的设计说明,**不是**实现 PR。目标是在**不削弱 ReAct 业务自由度**的前提下,
堵住身份越权、补偿重复发放等可控性/安全性漏洞,并把贫瘠的 state 升级为"能让长链 ReAct 不迷路"
的结构化工作记忆。

升级方向严格对齐三条底层原则(见 ARCHITECTURE.md《Core doctrine》):

- **ReAct = 业务推进引擎**:模型仍自主决定下一步业务、可随对话中途切换业务。
- **LangGraph State = 可控机制**:state 必须承载"已知什么、工具验证了什么、有什么挂起、已经发生了什么"。
- **System-enforced safety**:模型的工具调用是**操作提案**,不是最终权力;是否执行由系统(schema /
  所有权校验 / 策略 / guardrail / HITL / 幂等 / 审计)裁决。

---

## 1. 现状审计(按严重度)

| 编号 | 级别 | 问题 | 代码位置 |
|---|---|---|---|
| P0-1 | 🔴 越权 | `user_id` 由**模型传参**而非会话绑定;所有权校验校的是"模型填的 user_id",可被提示注入/幻觉劫持 → 水平越权(IDOR) | `schema.py` 各 In 模型、`prompts.py:37-44`、`agent.py:83`、`impl.py:188-192` |
| P0-2 | 🔴 重复写 | `idempotency_key` 由**模型生成**;`issue_compensation` 仅按该 key 去重 → key 漂移会**重复发补偿** | `prompts.py:35-36`、`impl.py:163-165` |
| P0-3 | 🔴 无认证 | API `user_id` 直接来自请求体;`/trace/{session}` 零鉴权 | `app.py:44,93,104-109` |
| P1-1 | 🟠 失忆 | `AgentState` 仅 5 字段,无 intent/focus/plan/findings;长链靠消息历史"记忆",易迷路 | `state.py:8-13` |
| P1-2 | 🟠 漂移 | 高危名单 `_GATED` 硬编码,与 `registry` 的 `writes` 标志各说各话 | `agent.py:28` vs `registry.py` |
| P1-3 | 🟠 脆弱 | `interrupt()` 在循环内,HITL 恢复会重跑整个 `tools_node`;多写时确认会错配/丢失 | `agent.py:79-102` |
| P2-* | 🟡 健壮性 | 确认值未绑定动作;补偿无累计上限;Trace 不持久;退货窗口用冻结的 `NOW`;sqlite 单连接并发 | 见 §4 |

> **根因**:P0-1/P0-2/P0-3 是同一件事——**信任边界没建立**。身份与幂等键这类"系统应独占"的东西,
> 被交给了模型。这在身份维度上架空了第三条原则。

---

## 2. 核心设计澄清

以下每一条都是实现前必须先对齐的设计决策。**带 ⭐ 的是本次最关键的几条。**

### ⭐ D1 — 事实源 / digest 分离 + 实时渲染(状态回灌)

**问题**:把结构化 state 升级丰富之后,模型怎么"看见"它?最朴素的做法(把状态摘要 append 进消息历史)
会导致**多份过期快照层层堆积**,模型锚定到错误的那份。

**决策**:state 分两层,职责互不混淆。

| | 角色 | 存储 | 谁读 | 累积? |
|---|---|---|---|---|
| **结构化字段**(intent/focus/findings…) | **唯一事实源** | checkpoint 持久化 | **代码**用于控制 | 否,原地覆盖 |
| **state digest**(回灌给模型的那段文本) | 事实源的**一次性投影** | 不存储,调用时实时渲染 | **模型**用于保持方向 | **永不进历史** |

**实现要点**:digest 在调用 LLM 的那一刻由当前 state 重新渲染,拼进**本次请求**,但 `agent_node`
的返回值**只 append assistant 消息**——digest 用完即弃,绝不写回 `messages`。

```python
def agent_node(state: AgentState) -> dict:
    digest = render_digest(state)                 # 从当前结构化字段实时生成
    call_messages = [
        state["messages"][0],                     # system(不变)
        *state["messages"][1:],                   # 历史:不含任何 digest
        {"role": "system", "content": digest},    # 唯一一份,贴在最末尾(recency 最强)
    ]
    resp = litellm.completion(messages=call_messages, ...)
    return {"messages": [assistant_msg]}          # 注意:digest 不在返回里 → 不入历史
```

**两个推论(直接回答两个常见疑问)**:
1. *新状态取代旧的吗?* —— 结构化字段是**覆盖式**更新(见 D4),内存里永远只有一份当前值;digest 因为
   从不入历史,所以**没有过期副本可被记错**,模型看到的当前状态永远只有最新一份。
2. *模型把状态记串了怎么办?* —— 见 D2/D10:**危险动作从不采信模型对状态的复述**。digest 只负责导航,
   错了顶多是话术需澄清,**动不了执行**。

### ⭐ D2 — user_id 是会话注入的可信上下文,模型无权表达

**决策**:`user_id` 从所有工具 schema 中**删除**,模型连填的机会都没有。

- 唯一来源:已认证主体 → `state["user_id"]`(可信、只读)。
- 唯一注入点:`tools_node` 在 `guard_write` 和 `dispatch` 之前,把 `state["user_id"]` 写进 args。
- `impl.py` 仍保留 `user_id` 形参,但由**系统**填充,所有权校验 `_owned_order` 校的是**会话用户**。
- 提示词删除 `{user_id}` 行与"include user_id"指令。

```python
# tools_node 内,执行每个工具前:
CUSTOMER_SCOPED = {"get_order","get_shipment","get_coupon",
                   "check_return_eligibility","create_return_request",
                   "issue_compensation","escalate_to_human"}
if name in CUSTOMER_SCOPED:
    args["user_id"] = state["user_id"]   # 系统注入,覆盖模型任何输入
```

### ⭐ D3 — idempotency_key 由系统确定性派生

**决策**:从 schema 删除 `idempotency_key`,模型不再提供。系统在 `tools_node` 按业务身份确定性生成:

- `create_return_request`:`key = (thread_id, "return", order_id, item_id)`
- `issue_compensation`:`key = (thread_id, "comp", reason_norm, amount)`

同一逻辑动作无论模型重试几次,key 恒定 → 彻底消除 P0-2 重复发补偿。

### D4 — State 字段定义与 reducer 选择(覆盖 vs 合并)

```python
class AgentState(TypedDict, total=False):
    messages: Annotated[list[dict], operator.add]   # 唯一 append 语义
    user_id: str            # D2:可信、系统注入、模型只读
    model: str
    steps: int
    intent: str | None      # 当前业务意图;切换见 D8
    focus: dict             # {order_id, item_id} 当前焦点
    plan: list[dict]        # checklist:[{step, status}]
    task_status: str        # gathering_info|awaiting_confirmation|escalated|resolved
    pending_action: dict | None  # 挂起的写:{tool,args,amount,token}(见 D7)
    findings: Annotated[dict, merge_findings]  # 已验证结论的累积缓存(合并语义)
    meta: dict
```

- 不带 reducer 的字段(intent/focus/task_status/pending_action)= **最后写入覆盖**。内存只有一份当前值。
- `findings` 用**合并型 reducer**(`{**old, **new}`),让"又查出 item B 的退款额"是**增量合并**,
  而不是把 item A 的结论清掉。`plan` 同理可用 by-step 合并。
- 选择标准:**单值状态用覆盖,累积证据用合并**。

### D5 — State 由系统维护,模型不可直接写

intent/focus/findings 等由 `tools_node` **根据真实工具结果**更新(例如成功 `get_order` → 写 focus;
`check_return_eligibility` 返回 → 写 findings),**不让模型自报状态**。保持"系统是事实的权威"这一原则。

### D6 — 高危名单单一来源 + "是否需 HITL" 作为属性

删除 `agent.py:28` 硬编码 `_GATED`。改为读 `registry`:在 `ToolDef` 上增加属性区分
**写(writes)** 与 **需确认(requires_hitl)**——写 ≠ 一定需确认(如 `escalate_to_human` 是写但
不需 HITL 确认)。gating 逻辑统一从 registry 读取。

### D7 — HITL 恢复安全化(token 绑定 + 单写 gate)

- **每个节点最多 gate 一笔写**:若一条 assistant 消息含多个待确认写,只处理第一个,其余推迟到下一轮,
  避免恢复时重跑导致的错配/丢确认(P1-3)。
- **确认值绑定动作**:`interrupt()` 时把 `pending_action.token`(动作指纹)写入 state;`confirm(decision)`
  恢复时校验 token 一致**且** state 未变,才执行。杜绝"yes 批到了另一笔动作"。
- 写工具仍保持执行幂等(D3 + DB 去重),作为兜底。

### D8 — 业务切换(intent switch)的状态处理

ReAct 中途切业务是**特性不是 bug**。切换时:
- `intent` 覆盖为新意图;
- `focus` 是否继承取决于新意图是否同 order(如"退货"→"查这单物流"应继承 order_id);
- 未完成的 `pending_action` 在切换时**不丢弃**,而是标记并在 digest 中提示("你还有一笔退款待确认");
- digest 显式展示"当前意图 + 上一意图的未决事项",让模型切回时能接上。

### D9 — digest 的字段取舍与格式

digest 要**短、稳定、可机读感强**(降低模型误读)。建议固定模板:

```
[当前状态]
意图: returns(由 shipping 切换而来)
焦点: order=O123 item=I2
已确认结论: I2 可退, 退款额 $45, 未触发人工
进度: [x]查单 [x]查物流 [x]查可退性 [ ]创建退货单(待你确认)
待决: 一笔 create_return_request 等待客户确认
```

原则:只放**已被工具验证**的结论与进度;不放原始工具 JSON(那在历史里);金额/ID 用系统真实值。

### ⭐ D10 — 控制决策从不信任模型的复述(权威边界)

digest 是**导航**,不是**权威**。凡危险动作,系统都从 state / DB 现值**重新推导**:

| 决策 | 权威来源(代码) | 绝不采信 |
|---|---|---|
| 操作哪个用户 | `state["user_id"]`(D2) | 模型填的 user_id |
| 幂等键 | 系统派生(D3) | 模型给的 key |
| 是否可退 / 退多少 / 是否需人工 | `guard_write` 重算(读 DB)(`guardrails.py`) | 模型说的金额/结论 |
| 是否需 HITL | registry 属性(D6) | 模型自述"低风险" |

最坏情况:模型在话术里把金额/item 记串 → 需要一句澄清,**不可能**变成"给错人退款"。

### D11 — API / MCP 信任边界

- **API**:`user_id` 由 token/会话解析,不信任请求体;`/trace` 加鉴权(仅 trace 所属用户/管理员)。
- **MCP server**:`user_id` 必须来自**已认证的 MCP 连接上下文**,从工具签名移除(与 D2 一致),
  而不是当作普通入参——否则 MCP 是另一个越权面。

### D12 — 其它正确性澄清

- **Trace 持久化**:审计事件落库并按 `thread_id` 关联,重启后可查(当前是内存对象,易失)。
- **时间真实化**:退货窗口比较改用可注入 clock(eval 注入固定 `NOW`,生产用 `utcnow()`),
  消除 `from seed import NOW` 的上线隐患。
- **补偿累计上限**:`_guard_compensation` 增加按用户的滚动累计封顶,而非只看单笔 `amount>=20`。
- **并发**:checkpointer 连接按线程隔离 / 连接池(已开 WAL,缓解了一部分)。

---

## 3. 分阶段计划

```
阶段 A(信任边界, P0) ──┐
                      ├─ 建议合并为一个版本(共享 tools_node 注入管线)
阶段 B(结构化 state, P1)┘
阶段 C(健壮性, P2) ── 滚动跟进
```

- **阶段 A**:D2(user_id 注入)+ D3(幂等派生)+ D11(API/MCP 边界)。
- **阶段 B**:D1(digest 实时渲染)+ D4/D5(state 字段与 reducer)+ D6(单一名单)+ D8(切换)+ D9(digest 模板)。
- **阶段 C**:D7(HITL 恢复)+ D10 兜底加固 + D12(trace/clock/cap/并发)。

A 与 B 都改 `tools_node` 注入逻辑,**合并交付**避免改两遍。

---

## 4. 验收测试矩阵

| 设计点 | 必过测试 |
|---|---|
| D2 | 模型传错/伪造 user_id 时,系统注入覆盖之,跨用户访问被拒(扩展 `tests/test_tools.py`) |
| D3 | 同一逻辑动作多次重试只产生一笔补偿(`tests/test_tools.py`) |
| D1 | 历史中永不出现第二份 digest;长链下 focus 不丢(新 `tests/test_state.py`) |
| D7 | 多写时只 gate 一笔;错 token 的 confirm 被拒(`tests/test_hitl.py`) |
| D10 | 模型复述错误金额时,guardrail 仍按 DB 真值裁决(`tests/test_hitl.py`) |
| D11 | 未认证请求被拒;`/trace` 越权访问被拒(`tests/test_api.py`) |

---

## 5. 已定决策(Resolved · 2026-06-27)

1. **认证方案 → A(demo 级)**:服务端做 `bearer token → user_id` 映射并解析,**不信任请求体**;
   接口上预留真实身份源(OIDC/JWT)的扩展点。影响 D2/D11。
2. **focus 继承策略 → 浅栈**:同 order 的意图切换继承 `focus`;跨 order 切换则更新 `focus`,
   但用一个**浅栈**记住上一单,便于"切回去"。影响 D8。
3. **digest 预算 → 硬上限 ≤300 token**:`plan` 只显示最近 N 步 + 未决项;`findings` 只保留
   当前 `focus` 相关项。影响 D9。
4. **findings 失效 → 仅用于展示**:`findings` 只喂 digest,**不作决策依据**;任何危险动作前
   一律以 `guard_write` 重算 DB 真值为准,故 findings 过期也不会导致错误执行。影响 D4/D10。

---

## 6. 实现状态(Shipped · 2026-06-27)

**已交付(阶段 A + B 合并版,74 unit tests + 12 回归全绿):**

- D2 user_id 会话注入:`registry.openai_spec` 剥离 `SERVER_INJECTED` 字段;`agent.tools_node`
  经 `_inject_server_fields` 从可信 `state["user_id"]` 注入(无会话用户则 fail-closed)。
- D3 幂等键系统派生:`digest.derive_idempotency_key`。
- D11 API bearer 认证 + `/trace` 归属校验:`api/auth.py`、`api/app.py`、`web/index.html`。
  MCP 维持原签名,加信任边界说明(见 `mcp_server/server.py`)。
- D4/D5 结构化 state + `merge_dict` reducer;`digest.apply_tool_effect` 由工具事实推进状态。
- D1/D9 `digest.render_digest`:每轮实时渲染、≤1200 字符、focus-scoped、**不入 messages**。
- D6 `registry.GATED_TOOLS` 单一来源。D8 focus 浅栈(cap 3)。
- 测试:`tests/test_security.py`、`tests/test_state.py`、`test_api` 认证、`test_prompts`/`test_hitl`
  更新;动作级数据集 `eval/datasets/security_tasks.jsonl` + `refund_tasks.jsonl` 多意图/跨单切换。

**独立 QA(运维测试 agent)发现并已修复的失败案例:**

- 🔴 **补偿重复发放(double-spend)**:`derive_idempotency_key` 原先直接哈希解析后的 `amount`,
  `json.loads("15")`(int)与 `"15.0"`(float)`repr` 不同 → 两个 key → 重复发补偿。**已修**:
  金额归一化为 `f"{float(x):.2f}"`,并把 `user_id` 纳入 key 兜底。回归测试已加。
- 权衡说明:补偿键按 `(thread, user, reason, amount)` 派生 → 同一工单内 reason+amount 相同的两笔
  补偿会被视为同一动作(dedup 优先于重复付款);不同笔请用不同 reason。
- `render_digest` 对畸形 state 加 `isinstance` 容错(每轮都跑,不能崩)。

**阶段 C 已完成(92 unit + 12 回归全绿):**

- ✅ **C1 / D7 HITL 恢复硬化**:每轮最多 gate 一笔 confirm-write(`hitl_used`),其余 `deferred`;
  `interrupt` 带 `action_token`,`resume` 支持 `{"decision","token"}` 且 token 不匹配 fail-closed。
- ✅ **C2 退货窗口可注入时钟**(`clock.now()`:override→`RETAILCARE_NOW`→`utcnow`)。
- ✅ **C3 补偿按用户累计上限**(`store.COMP_CUMULATIVE_CAP`,排除同 idempotency_key)。
- ✅ **C4 Trace 持久化**(`trace/store.py` 按 thread_id 落盘,`/trace/thread/{id}` 重启可查 + 归属校验)。
- ✅ **C5 checkpointer 并发**(`PRAGMA journal_mode=WAL` + `busy_timeout=5000`)。
- ✅ **C6 认证 JWT 化 + MCP 身份绑定**(`RETAILCARE_JWT_SECRET` 走 HS256 校验;MCP 工具移除
  `user_id`,由 `RETAILCARE_MCP_USER` 绑定,fail-closed)。

**后续(尚未做):** RS256/JWKS/OIDC、MCP 写操作系统派生幂等、guard↔write 的 TOCTOU 收敛。
