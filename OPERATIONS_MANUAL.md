# RetailCare Orchestrator — 执行操作手册(Operations Manual)

> **权威性声明**:本手册是项目自主迭代的**唯一执行依据**。唯一的需求来源是 `RetailCare_Orchestrator_项目定义_v1.md`(下称"v1 定义")。设计文档以 v1 为准(v2 作废)。
> 任何实现决策若与 v1 定义冲突,以 v1 定义为准;若 v1 定义未覆盖,按本手册的"自主决策协议"(§8)处理。
>
> 维护规则:每完成一个里程碑,更新本文件顶部的「进度看板」与对应里程碑的「实际交付」字段。

---

## 0. 进度看板(每次迭代更新)

| 里程碑 | 状态 | 完成日期 | Git Tag | 备注 |
|---|---|---|---|---|
| M0 工程地基 | 🔨 进行中 | — | — | 仓库/CI/配置/模型接入；3.14 全栈验证通过，DeepSeek ping ✅ |
| M1 单 Agent 基线 | ⏳ 未开始 | — | — | 工具层+mock+L0 Agent+trace |
| M2 退款风控闭环 | ⏳ 未开始 | — | — | RAG+幂等+HITL+故障注入+自建评测集 |
| M3 评测与消融 | ⏳ 未开始 | — | — | 指标体系+错误分类+E1/E3/E4+eval CI |
| M4 收尾交付 | ⏳ 未开始 | — | — | Web前端+E2/E5/E6 选做+文档+Demo |

状态图例:⏳ 未开始 / 🔨 进行中 / ✅ 已交付 / ⚠️ 受阻(见 §8.4 受阻登记)

---

## 1. 项目北极星(一句话)

构建一个**评测驱动的电商售后 Agent 可靠性系统**:接住 5 类售后意图,以**退款全链路**为 hero task,用严谨评测(pass^k、动作级合规、错误分类、Pareto)证明它**可靠、合规、不越权、可恢复、可回归**。

**主轴**:可靠性 × 可评测。其余皆为支线,不为堆关键词硬加模块。

---

## 2. 最终验收闭环(6 条全中才算交付)

这是**终局验收标准**,也是防止"自我钻死胡同"的最终标尺。任何阶段做的事都要服务于这 6 条:

| # | 验收维度 | 客观证据(必须可被第三方复现) |
|---|---|---|
| ① | **真实业务规则** | `BUSINESS_RULES.md` + 可执行的政策/资格规则,RAG 命中片段带版本号 |
| ② | **端到端可运行** | `make demo` 或一条命令能跑通"用户提退款诉求 → 资格判断 → 确认/升级 → 幂等执行 → 回执",含 Web 前端 |
| ③ | **可观测 (trace)** | 每次工具调用/中断/失败原因落盘为结构化 JSON,可在前端可视化 |
| ④ | **可恢复 (checkpoint/HITL)** | LangGraph `interrupt()` 高风险中断 + checkpointer 恢复,跨会话续单可演示 |
| ⑤ | **可评测 (benchmark)** | `eval/` 能一键跑出全部指标(§7)+ 置信区间;BFCL + 自建退款集都能跑 |
| ⑥ | **可回归 (CI)** | 每次提交自动跑小规模 eval,基线回归即失败(红灯) |

> **终局自检问题**(每个里程碑结束都问一遍):"我现在做的事,把这 6 条里的哪一条往前推了?如果都没推,为什么在做它?"

---

## 3. 系统架构与技术栈(锁定,不再发散)

**架构(v1 = 单 Agent 形态 / 设计 v1 §4)**:
```
用户 → 主 Agent(LangGraph StateGraph, ReAct):意图识别 + 工具路由 + 多轮管理
   ├─ 只读工具: get_order / get_shipment / search_policy / get_coupon / check_return_eligibility
   ├─ 政策 RAG 组件(检索 + 版本化引用)
   ├─ 风控/Guardrail 校验器(写操作前: 参数完整性 + policy check + 幂等键)
   ├─ HITL 中断点(interrupt(): 等用户确认 / 人工)
   ├─ 写操作工具: create_return_request / issue_compensation
   └─ 升级出口: escalate_to_human
记忆: 短期 state + 工单摘要(checkpointer 持久化)
Trace: 每次工具调用/中断/失败原因落盘 JSON
```

**技术栈(锁定 / 设计 v1 §11)**:
- 语言/编排:Python 3.11+ · **LangGraph**(StateGraph / checkpointer / `interrupt()` HITL)
- 模型层:**LiteLLM 兼容层**,多模型可切;**主力模型 = DeepSeek v4**(见 §11 待提供输入)
- 工具契约:**Pydantic**;工具层**通过 MCP 暴露**,独立可单测
- 检索:**FAISS 或 Chroma**(政策 RAG)
- 服务/前端:**FastAPI** + 轻量 Web 前端(可视化对话 + trace)
- 数据:SQLite(订单/工单 mock)
- 评测:pytest + **eval 回归 CI**(GitHub Actions)
- 可观测:结构化 JSON trace(LangSmith/Phoenix 可选增强)
- 容器:Docker
- **语言路线:英文为主(按 v1 定义,已与用户确认)**

**数据三层(设计 v1 §8)**:
| 层 | 数据 | 用途 |
|---|---|---|
| 对话真实性 | Bitext retail-ecommerce + customer-support | 意图分类、话术、用户模拟器、RAG FAQ 语料 |
| 工具调用评测 | BFCL v4 | 工具选择/参数正确率(含 multi-turn) |
| 任务级评测 | **自建退款任务 30–50 条**(标 `evaluation_criteria.actions`)+ τ³-bench retail 打底 | 任务成功率/合规/pass^k |

---

## 3.5 开发环境声明(Dev Environment)⭐

> 无人监督迭代时,环境一致性是闭环可复现的前提。本节声明**本机实测环境**、**项目目标环境**、**已知风险与对策**、**搭建步骤**。所有版本均为本机真实探测结果(非假设)。

### 3.5.1 本机实测环境(2026-06-16 探测)

| 项目 | 实测值 | 说明 |
|---|---|---|
| 操作系统 | macOS 15.6.1 (Build 24G90) | Sequoia |
| 架构 | **arm64 (Apple Silicon)** | 选依赖 wheel 时注意 arm64 |
| Shell | zsh (`/bin/zsh`) | — |
| Python | **3.14.2**(`/Library/Frameworks/Python.framework/Versions/3.14`) | ⚠️ 过新,见风险 R1 |
| Node | v24.14.1 / npm 11.11.0 | 用于 Web 前端 |
| Git | 2.39.5 (Apple Git-154) | 可用 |
| Homebrew | **未安装** | ⚠️ 见风险 R2 |
| Docker | **未安装** | ⚠️ 见风险 R3 |
| gh CLI | **未安装** | 见 §9 / 风险 R2 |

### 3.5.2 项目目标运行环境(锁定)

| 项目 | 目标 | 理由 |
|---|---|---|
| Python | **3.12.x**(项目专用 venv,不用系统 3.14) | langgraph/litellm/faiss/chromadb/fastapi 在 3.12 上 wheel 齐全、最稳 |
| 依赖管理 | `venv` + `requirements.txt`(**全部 pin 精确版本**) | 可复现;锁文件入库 |
| 向量库 | 优先 **Chroma**(纯 Python 友好);FAISS 作为备选 | 规避 arm64 + 新 Python 下 faiss 装不上的风险 |
| 隔离 | 所有依赖装在 `.venv/`,**不污染系统 Python** | — |
| 环境变量 | 根目录 `.env`(被 `.gitignore` 忽略),`.env.example` 入库 | key 绝不入库 |

### 3.5.3 已知风险与对策(R1–R3)

- **R1 — Python 3.14 过新**:多数 ML/Agent 依赖尚无 3.14 wheel,直接用会编译失败。
  **对策**:为项目创建 **3.12 venv**。若本机无 3.12 → ① 请用户安装(python.org 安装包,无需 brew);② 若坚持自主推进,先尝试 3.14 + 纯 Python 依赖(Chroma 而非 FAISS),遇到装不上的包按 §8.3 降级换库;③ 实在不行将其登记为受阻项并通知用户。
- **R2 — 无 Homebrew**:装 `gh` CLI 受阻。
  **对策**:① 用 `git` + Personal Access Token(HTTPS remote)即可完成 push/回滚,**不强依赖 gh**;② 如需 gh,可下载官方 release 二进制,或请用户装。GitHub 接入不阻塞开发本身。
- **R3 — 无 Docker**:M4 的容器化交付物无法本地验证。
  **对策**:Docker 化作为**最后收尾的可选增强**,不阻塞 M0–M3 的核心闭环;`Dockerfile`/`docker-compose.yml` 照常写好,本地验证需用户装 Docker Desktop(登记为待用户输入)。

> 原则:**环境问题一律走"先用纯 Python/本地方案跑通闭环,容器化与 CLI 工具作为增强"**,绝不因为缺 brew/docker 而卡住核心里程碑。

### 3.5.4 环境搭建步骤(M0 执行,写进 README & Makefile)

```bash
# 1. 创建项目专用 venv(优先 3.12;若只有 3.14 见 R1)
python3.12 -m venv .venv || python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖(版本全部 pin)
pip install -U pip
pip install -r requirements.txt

# 3. 配置模型 key
cp .env.example .env   # 填入 DeepSeek v4 key / base_url / model id

# 4. 冒烟验证
make test              # pytest 骨架
python -m retailcare.config --ping   # 真实调用 DeepSeek v4
```

### 3.5.5 可复现性要求
- `requirements.txt` 必须 **pin 精确版本**;锁文件入库。
- README 注明:目标 Python 3.12、arm64 macOS 实测;CI 用相同 Python 版本。
- 任何"在我机器上能跑"都不算数 —— 以 **CI 绿灯** 为可复现的客观证据。

---

## 4. 目标仓库结构

```
RetailCare-Orchestrator/
├── README.md                  # 项目总览 + quickstart
├── ARCHITECTURE.md            # 架构与设计推导
├── BUSINESS_RULES.md          # 退款政策与资格规则(可被代码与 RAG 引用)
├── OPERATIONS_MANUAL.md       # 本手册
├── pyproject.toml / requirements.txt
├── Makefile                   # make setup/test/eval/demo/serve
├── .env.example               # 模型 key/endpoint 模板(不含真 key)
├── docker-compose.yml
├── src/retailcare/
│   ├── config.py              # LiteLLM/模型配置(读 env)
│   ├── tools/                 # Pydantic 契约 + 工具实现(只读/写)
│   │   ├── schema.py
│   │   └── impl.py
│   ├── mcp_server/            # MCP 暴露工具层
│   ├── data/                  # mock 订单/工单 SQLite + seed
│   ├── policy/                # 政策文档 + RAG 索引构建
│   ├── graph/                 # LangGraph 状态图(主 Agent + 退款子图)
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── guardrails.py      # 风控校验器 + 幂等
│   │   └── build.py
│   ├── memory/                # 短期 state + 工单摘要
│   ├── trace/                 # 结构化 trace 落盘
│   └── api/                   # FastAPI 服务
├── web/                       # 轻量前端(对话 + trace 可视化)
├── eval/
│   ├── datasets/              # 自建退款集 + BFCL 适配 + τ³ 打底
│   ├── runner.py              # 评测执行器(多 seed/多 run)
│   ├── metrics.py             # 全部指标 + 置信区间 + pass^k
│   ├── judge.py               # LLM-as-judge 初筛
│   ├── error_taxonomy.py      # 错误打标
│   └── experiments/           # E1–E6 配置与脚本
├── reports/
│   ├── baseline_report.md
│   ├── ablation_report.md
│   └── error_taxonomy.md
├── tests/                     # pytest 单测(工具/guardrail/幂等/恢复)
└── .github/workflows/eval.yml # eval 回归 CI
```

---

## 5. 里程碑总览(M0–M4)

> 每个里程碑都有:**目标 → 任务清单 → 交付物 → 验收门(必须全过)→ 通知点**。
> **验收门是硬门槛**:门没过不进下一里程碑。门过了打 git tag 并通知。

设计 v1 的 W1–W7 映射:M0(地基)→ M1(W1–2)→ M2(W3–4)→ M3(W5–6)→ M4(W7)。

---

### M0 — 工程地基

**目标**:把仓库、配置、模型接入、CI 骨架、测试骨架立起来,保证后面每一步都能被验证。

**任务清单**:
- [ ] git init + 连接 GitHub 远程(见 §9)
- [ ] 初始化 Python 工程(pyproject/requirements + 虚拟环境)
- [ ] `config.py`:通过 LiteLLM 接入 **DeepSeek v4**,写一个最小 `ping_model()` 冒烟测试
- [ ] `.env.example` + `.gitignore`(确保真 key 不入库)
- [ ] `Makefile`:setup/test/lint/eval/serve/demo 占位
- [ ] pytest 骨架 + 一条 `test_smoke.py`
- [ ] GitHub Actions 骨架(先只跑 lint + smoke test)
- [ ] `README.md` 初版 + 本手册入库

**交付物**:可 `make setup && make test` 通过的空壳仓库 + 一次成功的模型调用日志。

**验收门 G0**:
1. `make test` 绿;
2. `python -m retailcare.config --ping` 能成功调用 DeepSeek v4 并返回内容;
3. CI 在 GitHub 上跑出绿灯;
4. 远程仓库可见首个 commit。

**通知点 N0**:G0 全过 → 通知"地基就绪,模型接入打通"。

---

### M1 — 单 Agent 基线(对照组 L0)

**目标**:工具层 + mock 数据 + 单 Agent(全工具 + 政策写进 prompt)+ trace 落盘,跑通 5 类意图的基本对话,拿到 pass@1 / pass^k 基线数字。

**任务清单**:
- [ ] `tools/schema.py`:8 个工具的 Pydantic I/O 契约(设计 v1 §5),写操作强制 `idempotency_key`
- [ ] `tools/impl.py` + `data/`:mock 订单/物流/优惠券/工单 SQLite + seed 数据
- [ ] 工具单测(每个工具 happy path + 边界)
- [ ] `mcp_server/`:工具层通过 MCP 暴露,可独立调用
- [ ] `graph/`:单 ReAct Agent,意图识别 + 工具路由 + 多轮 state
- [ ] `trace/`:每次工具调用/失败落盘结构化 JSON
- [ ] Bitext 数据接入(意图语料 / 用户模拟器素材)
- [ ] 跑通 5 类意图的最小端到端对话(CLI)

**交付物**:能跑的 L0 baseline + `reports/baseline_report.md`(基线数字 + trace 样例)。

**验收门 G1**:
1. 8 个工具单测全绿,写操作无 `idempotency_key` 必拒;
2. CLI 能完成 5 类意图各至少 1 条对话,trace 文件生成且结构合法;
3. 单 Agent 能在自建退款集(哪怕 5–10 条先行样本)上跑出 pass@1 数字并落到 baseline_report;
4. MCP server 能被独立 client 调用成功。

**通知点 N1**:G1 全过 → 通知"L0 基线跑通 + 基线指标"。

---

### M2 — 退款风控闭环(可靠性加固 L1)⭐ HERO

**目标**:把退款做穿——政策 RAG + 资格判断 + 参数完整性校验 + policy check + 幂等 + HITL 确认/升级 + 故障注入恢复,全程 trace。这是项目最硬的部分。

**任务清单**:
- [ ] `BUSINESS_RULES.md`:退款政策 + 资格规则(金额阈值、原因分类、时效窗口等),可被代码与 RAG 引用
- [ ] `policy/`:政策文档切块 + FAISS/Chroma 索引 + **版本化引用**(命中片段带 version 写进 trace)
- [ ] 退款状态机(设计 v1 §6):取订单 → 检索政策 → 资格判断 → [缺失]澄清 → [合规且低额]确认→幂等执行 → [高额/异常/冲突]升级
- [ ] `guardrails.py`:写操作前置校验(参数完整性 + policy check)+ **幂等键 =(order_id, item_id)**
- [ ] HITL:LangGraph `interrupt()` 在高风险节点中断,确认/人工后从 checkpoint 恢复
- [ ] 跨会话恢复:checkpointer 持久化,演示"隔天续单"
- [ ] 故障注入:工具 timeout/报错/过期数据 → 重试 → 兜底话术 → 升级,并写故障注入测试
- [ ] 工单摘要记忆(短期 state + 摘要)
- [ ] **自建退款评测集 30–50 条**,标 `evaluation_criteria.actions`(τ³ 范式)
- [ ] BFCL v4 接入(工具选择/参数正确率)

**交付物**:生产级退款闭环 + `BUSINESS_RULES.md` + 自建退款评测集 + 故障注入测试套件。

**验收门 G2**:
1. 同一 `(order_id, item_id)` 重复/重试请求**绝不二次退款**(幂等测试通过);
2. 高额/异常一定走 `escalate_to_human`,低额合规走确认执行(分流测试通过);
3. HITL 中断后能从 checkpoint 恢复完成;跨会话续单可演示;
4. 故障注入下系统按"重试→兜底→升级"降级,不崩、不乱退;
5. RAG 命中政策片段带 version 并写入 trace;
6. 自建退款集 ≥30 条,可被 eval runner 加载并跑出动作级评测。

**通知点 N2**:G2 全过 → 通知"退款 hero 闭环达成 + 加固前后对比数字"。

---

### M3 — 评测体系与消融

**目标**:把指标体系、错误分类学、关键消融(E1/E3/E4)、eval 回归 CI 全部落地。这是项目主战场。

**任务清单**:
- [ ] `eval/metrics.py`:全部指标(§7)+ 多 seed/多 run + **置信区间** + **pass^k**
- [ ] `eval/runner.py`:一键跑全套,输出结构化结果 + 成本/token 统计(从第一天就量)
- [ ] `eval/judge.py`:LLM-as-judge 初筛 + 人工抽检校准接口
- [ ] `eval/error_taxonomy.py`:8 类错误打标(设计 v1 §9)→ `reports/error_taxonomy.md`
- [ ] **E1(主)**:L0 单 Agent vs L1 加固 vs L2 拆退款子图 → pass^k/违规率/p95/cost
- [ ] **E3**:政策接入方式(prompt / RAG / 高风险前强制 check)→ 违规率/引用准确率/延迟
- [ ] **E4**:高风险工具(直接执行 / 确认 / 人工升级)→ 误操作率/解决率/轮次
- [ ] `reports/ablation_report.md`:实验结论 + 图表
- [ ] eval 回归 CI:每次提交跑小规模 eval,基线回归即红灯

**交付物**:`ablation_report.md` + `error_taxonomy.md` + 工作的 eval CI。

**验收门 G3**:
1. `make eval` 一键跑出全部指标 + 置信区间 + pass^k;
2. E1/E3/E4 三个实验各有可复现结果与诚实结论(含负结论也算过);
3. 错误分类学能对 trace 自动打标并产出报告;
4. eval CI 能在基线回归时让 PR 变红(用一次故意回归验证拦截生效)。

**通知点 N3**:G3 全过 → 通知"评测闭环 + E1/E3/E4 结论"。

---

### M4 — 收尾交付

**目标**:轻量 Web 前端 + 选做实验 + 完整文档 + Demo,凑齐 6 条验收闭环并交付。

**任务清单**:
- [ ] `web/`:对话界面 + trace 可视化(工具调用/中断/政策引用/失败原因)
- [ ] `make demo` 一条命令端到端演示
- [ ] 选做:E2(路由)/ E5(记忆)/ E6(强弱模型混合 → 质量×成本 Pareto 前沿图)——有余力才做,不强求
- [ ] `README.md`(quickstart + 结果摘要)、`ARCHITECTURE.md`(架构推导)定稿
- [ ] Demo 录屏/截图
- [ ] 最终自检:§2 的 6 条逐条对照证据

**交付物**:完整可运行系统 + 全套文档 + 报告 + Demo。

**验收门 G4(= 终局验收)**:§2 的 6 条全部有客观证据。

**通知点 N4**:G4 全过 → **项目交付通知**(含仓库地址、Demo、关键指标、6 条验收对照表)。

---

## 6. 评测端到端闭环定义(必须真实跑通)

闭环 = `数据 → 运行 Agent → 采集 trace → 计算指标 → 错误分类 → 报告 → CI 守门`,一条命令可复现:

```
make eval        # 加载数据集 → 多 seed 跑 Agent → 落 trace → 算指标(含 pass^k/CI) → 出报告
```

**真实性硬要求**:
- 评测必须**真实调用 DeepSeek v4**(不允许 mock 掉模型来"假绿");
- 结果必须含**多次运行的均值 + 置信区间**(任务量小,单次数字不可信);
- 核心结论用 **pass^k** 而非 pass@1;
- 从第一次评测起就记录 **token / cost**,为 E6 Pareto 铺垫。

---

## 7. 评测指标(设计 v1 §9)

任务级:`task_success_rate`、**`pass^k`(核心)**、`avg_turns_to_resolution`、`latency_p95`、`cost_per_task`
工具级:`tool_call_accuracy`、`argument_accuracy`、`tool_failure_recovery_rate`
合规级:`policy_violation_rate`、`unnecessary_handoff_rate`、`human_escalation_precision`、`clarification_quality`

**错误分类学(8 类)**:意图路由错 / 工具选择错 / 参数缺失未澄清 / 工具顺序错 / 违反政策 / 过早升级 / 长上下文遗忘 / 答复与工具结果不一致。

---

## 8. 自主决策协议(防钻死胡同)⭐ 核心

这一节决定了"无人监督时我怎么不跑偏、不卡死"。

### 8.1 自主迭代节奏
- 在一个里程碑内**连续自主推进**:写代码 → 跑测试 → 修复 → 提交。
- 每完成一个有意义的单元(一个工具、一个节点、一组测试)就 **git commit**,信息清晰。
- 里程碑验收门通过 → 打 **git tag**(`m0`/`m1`/...)+ 发**通知**。

### 8.2 决策优先级(冲突时的裁决顺序)
1. v1 定义明确写了 → 照做。
2. v1 没写但本手册写了 → 照本手册。
3. 都没写 → 选**最简单、最能推进 §2 六条验收**的方案,并在 commit/报告里记录"为什么这么选"。
4. 涉及**不可逆 / 外发 / 花钱明显 / 安全**的动作(删大量文件、强推覆盖远程、对外发布、产生显著 API 花费)→ **停下来问用户**。

### 8.3 时间盒与放弃规则(避免无限纠缠)
- 任一技术障碍**连续 3 次**尝试仍未解决 → 停止硬刚,执行:
  (a) 记录到 §8.4 受阻登记;(b) 找**降级替代方案**绕过(如某依赖装不上 → 换等价库;τ³-bench 接不进 → 先用自建集打底);(c) 若替代也不行且阻塞里程碑验收门 → **通知用户并附具体选项**。
- 宁可用更朴素但能跑通闭环的方案,也不要为"优雅"卡在一个点上。**先闭环,再优化**。

### 8.4 受阻登记(出现即填,解决即划掉)
| 日期 | 受阻点 | 已尝试 | 当前对策 | 是否需用户 |
|---|---|---|---|---|
| — | — | — | — | — |

### 8.5 防"假完成"
- 不允许用 mock 掉模型/跳过断言的方式让测试/评测"假绿"。
- 每个验收门用**客观命令 + 输出**证明,而非口头声称。
- 报告里的指标必须是**真实跑出来**的,注明 seed、运行次数、模型版本。

---

## 9. Git / GitHub 工作流

- **分支**:`main` 保护;开发在 `dev` 或 `feat/*`,里程碑合并回 `main` 并打 tag。
- **提交粒度**:小而频繁,每个逻辑单元一次 commit。
- **里程碑 tag**:`m0`/`m1`/`m2`/`m3`/`m4`,便于回滚到任一里程碑。
- **回滚**:出问题用 `git revert`(保留历史)优先;必要时 `git reset --hard <tag>` 但**绝不强推覆盖远程**,除非用户明确同意。
- commit message 结尾署名(按环境规范)。
- **待用户操作**:见 §11 —— gh 认证 / 远程仓库地址。

---

## 10. 通知机制

- **通知点**:N0–N4(每个里程碑验收门通过时)+ 任何"受阻需用户决策"时。
- **通知内容模板**:里程碑名 / 验收门是否全过 / 关键交付物 / 关键指标 / git tag+commit / 下一步 / 是否需要用户做什么。
- **通知渠道**:**待用户确认**(邮件 zczqgm1@ucl.ac.uk / 桌面推送 / 仅会话内汇报)。在确认前,默认在**会话内**输出里程碑总结。

---

## 11. 待用户提供的输入(BLOCKING — 缺这些无法跑通端到端)

| # | 需要的东西 | 用途 | 现状 |
|---|---|---|---|
| 1 | **DeepSeek v4 API Key + base_url + 确切 model id** | 模型接入(M0 起全程必需,评测必须真调) | ❓ 待提供 |
| 2 | **GitHub 接入方式** | 版本控制 / 回滚 / 真实开发流程 | ❓ 待定(新建私有库 / 提供现有库 / 先本地) |
| 3 | **通知渠道确认** | 里程碑通知 | ❓ 待定(默认先会话内) |
| 4 | **自主程度确认** | 是否每个里程碑停下来等确认 | ❓ 待定(默认里程碑确认制) |
| 5 | **Python 3.12**(可选) | 规避 3.14 兼容性风险 R1 | ⚠️ 本机仅 3.14;装不上依赖时需要 |
| 6 | **Docker Desktop**(可选) | M4 容器化交付物本地验证 | ⚠️ 本机未装;不阻塞 M0–M3 |

> DeepSeek key 请勿直接贴在会话明文里若你介意——可写入项目根目录 `.env`(我会确保它在 `.gitignore` 中、绝不入库)。

---

## 12. Definition of Done(最终交付清单)

- [ ] §2 六条验收闭环全部有客观证据
- [ ] 全套交付物齐备:`README` / `ARCHITECTURE` / `BUSINESS_RULES` / `tools/schema.py` / `graph/` / `eval/` / `web/` / `reports/ablation_report.md` / `reports/error_taxonomy.md` / Demo
- [ ] `make demo` 端到端跑通(真实调用 DeepSeek v4)
- [ ] `make eval` 跑出全套指标 + 置信区间 + pass^k
- [ ] eval CI 在 GitHub 绿灯,且能在回归时变红
- [ ] 代码推送到 GitHub,里程碑 tag 齐全
- [ ] 进度看板(§0)全部 ✅

---

*执行锚点:先把"单 Agent + 工具层 + 退款风控闭环 + trace"在英文 mock 环境跑通(M0→M1→M2),再叠评测与消融(M3),最后收尾(M4)。先闭环,再优化。*
