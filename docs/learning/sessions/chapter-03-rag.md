# 第 3 章：RAG 技术

日期：2026-06-21

## 资料页码

- 资料第 54-57 页：RAG 的定义、离线/在线流水线，以及 RAG 与微调、长上下文的区别。
- 资料第 63-65 页：文档分块、chunk size、chunk overlap、父子块等策略。
- 资料第 67-71 页：Embedding、向量数据库、BM25、混合检索与 RRF。
- 资料第 74-75 页：重排序 / Reranking 与 MMR。
- 资料第 77-78 页：GraphRAG、Agentic RAG、Self-RAG、Corrective RAG。
- 资料第 79 页：RAGAS 与 faithfulness、answer relevancy、context precision/recall。
- 资料第 80-81 页：RAG 生产优化、多租户隔离、缓存、增量更新、Token 成本控制。
- 资料第 82 页：Agentic RAG 与一次性 RAG 的区别，RAGAS 的局限。

## 本章目标

理解 RetailCare 的 RAG 不是泛泛地“接了向量库”，而是：

```text
售后政策证据 RAG / Policy Evidence RAG
```

它的目标是把退货、退款、补偿、物流异常等业务政策变成可检索、可引用、可审计、可评测的证据。

## 知识点卡片 1：RAG 基础

知识点：RAG 的定义与两阶段流程

中英对照：检索增强生成 / Retrieval-Augmented Generation；离线索引 / Offline Indexing；在线检索 / Online Retrieval

资料依据：资料第 55、57、81 页。

资料原意：RAG 是在生成前先从外部知识库检索相关证据，再把证据作为上下文交给大模型，用来减少幻觉并支持知识更新。离线阶段负责解析、清洗、分块、向量化、建索引；在线阶段负责 query、检索、可选重排、拼接上下文和生成。

RetailCare 例子：RetailCare 把售后政策拆成版本化 policy chunks，例如 RET-001、RET-002、RET-003、RET-004、SHIP-001、COMP-001。Agent 在 RAG 模式下需要通过 `search_policy` 检索政策，而不是靠模型记忆或在 prompt 里硬背全部政策。

具体场景：用户问“高价值退款能不能自动处理？”系统检索到 RET-003：200 USD 及以上退款需要人工审核，然后再决定升级人工而不是自动退款。

项目证据：

- `BUSINESS_RULES.md` 声明政策是 authoritative、versioned policy。
- `src/retailcare/policy/store.py` 定义 6 个版本化政策 chunk。
- `src/retailcare/policy/rag.py` 用 Chroma 建 policy collection。
- `src/retailcare/tools/impl.py` 中 `search_policy()` 调用 RAG 检索。
- `src/retailcare/graph/prompts.py` 的 `SYSTEM_RAG` 要求需要政策时先调用 `search_policy`。

为什么这样设计：售后政策会变化，而且高风险退款必须可审计。把政策放到外部可检索存储里，比让模型“背政策”更容易更新、引用和追踪。

替代方案：把政策全文写进 system prompt。

为什么暂时不只用替代方案：prompt 内嵌政策简单，但政策更新要改 prompt，prompt 变长后噪声和维护成本上升，也不利于版本化引用。项目保留 `SYSTEM_L0` 作为对照组，但 `SYSTEM_RAG` 更符合可维护方向。

局限与后续扩展：当前 policy corpus 很小，离线 ETL 很简单，不涉及 PDF/Word 解析、大规模 chunking 或复杂元数据过滤。后续如果接入完整售后知识库，才需要完整 ETL。

面试表达：我项目里的 RAG 不是为了炫技做大规模知识库，而是针对售后政策这个高风险知识源做证据化。政策不应该只存在模型参数或 prompt 里，而应该变成可检索、可版本化、可审计的 chunk。

## 知识点卡片 2：分块与版本化

知识点：Chunking 与版本化引用

中英对照：分块 / Chunking；块重叠 / Chunk Overlap；版本化引用 / Versioned Citation

资料依据：资料第 63-65 页。

资料原意：chunk size 应覆盖完整命题；太小上下文不足，太大噪声多。chunk overlap 可以减少边界信息丢失，但会增加存储和冗余检索。

RetailCare 例子：RetailCare 的政策 chunk 每条都是一条完整业务规则，例如 RET-003 只描述高价值退款必须人工审核。这个粒度天然适合“完整命题”，因此当前不需要复杂 overlap。

具体场景：

```text
RET-003 = 高价值退款 >= 200 USD 需要人工审核
```

这条规则单独就是完整政策单元，检索命中后可以直接作为证据。

项目证据：

- `store._CHUNKS` 中每个 chunk 都有 `chunk_id`、`version`、`text`。
- `PolicyChunk` schema 包含 `chunk_id`、`text`、`version`、`score`。
- `BUSINESS_RULES.md` 用同样的 RET/SHIP/COMP 编号维护政策来源。

为什么这样设计：政策规则本身是结构化、短文本、边界清楚的，不需要为了“像通用 RAG”而强行做滑动窗口或父子块。

替代方案：把 `BUSINESS_RULES.md` 整篇按固定字符数切块。

为什么暂时不选替代方案：固定字符切块可能把一条政策切断，导致 RET-003 的阈值和人工审核要求分散在不同块里。对政策类知识，按业务规则手工分块更稳。

局限与后续扩展：如果未来政策文档变成长篇条款、FAQ 或合同，需要自动解析 Markdown 表格、标题层级和父子块。

面试表达：我没有机械用固定 token 切块，而是按业务规则切 chunk。因为售后政策的最小可引用单元就是一条规则，这样检索结果天然可解释、可审计。

## 知识点卡片 3：向量数据库与降级

知识点：Embedding 与向量数据库

中英对照：嵌入 / Embedding；向量数据库 / Vector Database；降级检索 / Fallback Retrieval

资料依据：资料第 67-71 页、第 80 页。

资料原意：Embedding 把文本映射成向量，向量数据库负责相似度检索；生产中还要考虑索引参数、缓存、增量更新和可用性。

RetailCare 例子：项目用 Chroma 的内置 ONNX MiniLM embedding 建 policy collection；如果 Chroma 或 embedding 层不可用，会 fallback 到 deterministic lexical search。

具体场景：查询 `high value refund human review` 时，当前 backend 是 Chroma，能命中 RET-003，并返回版本 `2026.06`。

项目证据：

- `policy/rag.py` 使用 `chromadb.EphemeralClient()`。
- collection 名为 `policy`，metadata 使用 cosine。
- 如果 `_COLLECTION is None`，调用 `store.search()` 词法检索。
- 验证命令显示 `backend=chroma`，命中 RET-003。

为什么这样设计：项目规模小，Chroma 足够轻；fallback 保证向量层坏了也不会让政策检索完全不可用。这符合售后系统“降级也要安全”的要求。

替代方案：Milvus、Qdrant、Elasticsearch、Postgres pgvector。

为什么暂时不选替代方案：当前只有 6 条政策 chunk，用重型向量数据库没有必要。项目重点是证明 RAG 与政策决策闭环，而不是做大规模向量库运维。

局限与后续扩展：如果政策库扩展到多租户、多产品线、多语言，需要持久化 Chroma 或迁移到 pgvector/Milvus，并加入 tenant_id、product_line、locale 等元数据过滤。

面试表达：我的选型是按规模来的。小型政策库用 Chroma 足够，关键是保留版本化 metadata 和 lexical fallback；等数据规模和多租户需求上来，再升级向量数据库。

## 知识点卡片 4：混合检索、重排与为什么暂时不做

知识点：Hybrid Search、RRF、Reranking、MMR

中英对照：混合检索 / Hybrid Search；倒排检索 / BM25；倒数排名融合 / Reciprocal Rank Fusion, RRF；重排序 / Reranking；最大边际相关性 / Maximal Marginal Relevance, MMR

资料依据：资料第 70-75 页。

资料原意：向量检索擅长语义相似，BM25 擅长精确词匹配；混合检索能提高鲁棒性。Reranking 能提升 Top-K 精度，但更慢。MMR 用来平衡相关性和多样性。

RetailCare 例子：RetailCare 当前没有做真正的 hybrid search、RRF 或 reranker。它是 Chroma vector search + lexical fallback。

具体场景：政策 chunk 很少，且每条有明确编号和短文本，Top-K 检索已经够用。比如“gift card refundable”应命中 RET-002，“high value refund”应命中 RET-003。

项目证据：

- `policy/rag.py` 只做 Chroma query，不做 BM25 融合和 rerank。
- `policy/store.py` 的 `search()` 是简单词法 overlap fallback。
- `tests/test_tools.py` 只要求 `search_policy` 返回带 version 的 chunks，没有测试 RRF 或 reranker。

为什么这样设计：当前瓶颈不是召回复杂文档，而是政策执行是否合规。复杂检索会增加维护成本，但对 6 条政策收益有限。

替代方案：向量 + BM25 + RRF + cross-encoder reranker。

为什么暂时不选替代方案：这套组合适合大规模企业知识库或编号/术语很多的文档库；RetailCare 当前政策语料太小，先做版本化和评测更有价值。

局限与后续扩展：如果后续政策库扩展到几千条 FAQ、商品类目规则、国家/地区规则，应该加入 BM25、RRF 和 reranker。

面试表达：我知道混合检索和重排是生产 RAG 常见方案，但我的项目没有为了堆技术而上复杂链路。当前政策库小、规则清楚，所以先用 Chroma + fallback，后续数据规模上来再引入 RRF 和 rerank。

## 知识点卡片 5：RAG vs Prompt vs 微调 vs 长上下文

知识点：RAG 与其他知识注入方式的取舍

中英对照：提示词内嵌 / Prompt-injection of knowledge；微调 / Fine-tuning；长上下文 / Long Context

资料依据：资料第 56、81 页。

资料原意：RAG 适合频繁更新、需要引用来源的事实知识；微调适合稳定行为和风格；长上下文不等于可治理、可检索、可更新。

RetailCare 例子：项目里同时保留两种政策进入方式：`SYSTEM_L0` 把政策写进 prompt，`SYSTEM_RAG` 要求通过 `search_policy` 检索。

具体场景：消融报告 E3 比较了 policy prompt 和 policy RAG。L1_policy_rag 的 pass^3 是 0.8，高于 L1_guardrails 的 0.6，且成本/延迟相近。

项目证据：

- `prompts.py` 注释说明 L0 baseline embeds policy；M2/E3 move it to RAG。
- `reports/ablation_report.md` 显示 L1_policy_rag 达到最好 pass^3。
- 报告也诚实说明：RAG 成功率接近 prompt，但一致性更好，并且解耦政策更新。

为什么这样设计：政策知识是“可更新事实”，不是模型能力本身。用 RAG 比微调更适合，因为改政策时不需要重新训练模型。

替代方案：微调模型记住售后政策，或者把所有政策塞进超长 prompt。

为什么暂时不选替代方案：微调不适合频繁变化的政策；长 prompt 会增加成本和噪声，也不利于版本审计。

局限与后续扩展：当前 E3 实验规模较小，不能过度宣称 RAG 全面优于 prompt。更准确说法是：RAG 在本项目里提升一致性和可维护性。

面试表达：我不会说 RAG 一定比 prompt 好。我的实验显示，在这个售后政策场景里，RAG 和 prompt 成功率接近，但 RAG 的一致性和可维护性更好，因为政策可以独立更新并保留版本。

## 知识点卡片 6：Agentic RAG

知识点：Agentic RAG

中英对照：智能体驱动的检索增强生成 / Agentic RAG；一次性 RAG / One-shot RAG

资料依据：资料第 77-78、82 页。

资料原意：普通 RAG 是一次检索后生成；Agentic RAG 由 Agent 决定何时检索、检索什么、是否再次检索，并可结合多工具循环。

RetailCare 例子：RetailCare 的 RAG 介于 one-shot RAG 和 Agentic RAG 之间。它不是一个复杂的多步 RAG 系统，但在 `SYSTEM_RAG` 下，Agent 会在需要政策时主动调用 `search_policy`，并结合 `check_return_eligibility`、`create_return_request`、`escalate_to_human` 等工具形成任务闭环。

具体场景：退款问题不是“检索政策后回答”就结束，而是政策检索可能影响后续工具动作：低价值确认、高价值升级、非退货阻断。

项目证据：

- `SYSTEM_RAG` 指示需要政策时调用 `search_policy`。
- `search_policy` 是 8 个工具之一，和订单、物流、退货工具处于同一行动空间。
- eval 数据集里同一类退款任务会根据政策走不同动作。

为什么这样设计：售后场景需要把政策证据接到行动决策上，而不是只生成文本答案。

替代方案：纯 one-shot RAG，只检索政策后回答用户。

为什么暂时不选替代方案：只回答政策不能完成退款任务，也无法验证是否创建退货、升级人工或阻断写操作。

局限与后续扩展：当前还没有 Self-RAG、Corrective RAG 或多轮重检索策略。未来可以在检索为空、证据冲突或工具结果不一致时触发二次检索。

面试表达：RetailCare 的 RAG 不是孤立问答模块，而是 Agent 工具空间的一部分。政策检索结果会影响后续动作，所以它具备一定 Agentic RAG 特征，但还不是复杂的 Self-RAG/Corrective RAG。

## 知识点卡片 7：RAG 评估

知识点：RAG 评估

中英对照：忠实度 / Faithfulness；答案相关性 / Answer Relevancy；上下文精确率 / Context Precision；上下文召回率 / Context Recall

资料依据：资料第 79、82 页。

资料原意：RAGAS 可用 LLM-as-judge 评估 RAG 管道，但裁判模型有偏好和盲区。生产中要结合任务指标、人工抽检和 badcase 归因。

RetailCare 例子：RetailCare 目前没有直接使用 RAGAS，而是用业务任务成功率、政策违规率、升级精度、pass^k 和错误分类来评估政策 RAG 是否真的帮到售后任务。

具体场景：RAG 检索对不对，最终要看是否阻止了 gift card 退款、是否把高价值退款升级人工、是否没有过度升级普通订单查询。

项目证据：

- `eval/datasets/refund_tasks.jsonl` 包含低价值退款、高价值退款、不可退商品、缺少信息等用例。
- `eval/metrics.py` 计算 pass^k、policy_violation_rate、unnecessary_handoff_rate、human_escalation_precision。
- `reports/baseline_report.md` 记录 pass@1、policy_violation_rate、escalation_precision 等指标。
- `reports/ablation_report.md` 比较 L1_guardrails 与 L1_policy_rag。

为什么这样设计：项目目标不是通用问答好看，而是售后动作正确、合规、可恢复。因此业务任务指标比单独 RAGAS 更贴近目标。

替代方案：引入 RAGAS，评估 faithfulness、context precision/recall。

为什么暂时不选替代方案：当前政策库小，关键是业务动作是否正确；RAGAS 更适合大规模问答 RAG 管道评估。

局限与后续扩展：如果后续接入大量政策文档和 FAQ，需要加入 RAGAS 或自建检索标注集，专门测 Recall@K、Precision@K、citation correctness。

面试表达：我没有只用 RAGAS，因为我的 RAG 是嵌在售后 Agent 决策里的。最终评估不是答案像不像，而是工具动作和政策合规是否正确。

## 知识点卡片 8：RAG 安全与多租户

知识点：RAG 安全、多租户隔离、Prompt 注入

中英对照：多租户 / Multi-tenancy；租户过滤 / Tenant Filtering；提示词注入 / Prompt Injection

资料依据：资料第 80-81 页。

资料原意：多租户下最常见的安全事故是检索未带租户过滤，导致跨租户数据泄露。还要注意文档污染和 Prompt 注入。

RetailCare 例子：当前 RetailCare 的 policy RAG 是全局公共政策，不是用户私有文档，所以不存在跨用户检索私有知识的问题。但订单、优惠券等用户数据必须通过工具按 user_id/order_id 控制，不能混入公共 RAG。

具体场景：退货政策 RET-003 对所有用户一样，可以作为全局知识；但用户的订单 O1001、优惠券 WELCOME10 不能进入公共 policy vector store。

项目证据：

- policy chunks 不含用户隐私，只含公共规则。
- 订单、优惠券、退货状态通过 DB 工具查询，不通过 RAG 检索。
- `BUSINESS_RULES.md` 要求高风险写操作走 policy check、confirmation/escalation、idempotency、audit。

为什么这样设计：公共政策适合 RAG，用户数据适合结构化数据库和权限控制。把两者混在同一个向量库会增加泄露风险。

替代方案：把所有订单、用户画像、聊天历史都放进向量库统一检索。

为什么暂时不选替代方案：这样会带来跨用户泄露、权限过滤和删除合规风险。当前项目优先保持边界清晰。

局限与后续扩展：如果以后做用户长期记忆或多租户商家知识库，必须给每条向量加 tenant_id/user_id 元数据，并在数据库层和查询层双重过滤。

面试表达：我把公共政策 RAG 和用户私有数据查询分开。公共规则可以向量检索，用户订单和优惠券必须走结构化工具和权限边界，这样能降低多租户 RAG 的数据泄露风险。

## 本章总图

```text
BUSINESS_RULES.md
  |
  v
policy/store.py: versioned chunks
  |
  v
policy/rag.py: Chroma vector search + lexical fallback
  |
  v
search_policy tool
  |
  v
Agent receives policy evidence
  |
  v
check_return_eligibility / guardrails / HITL / escalation
  |
  v
trace + eval metrics
```

## 验证

本节运行：

```bash
.venv/bin/python -m pytest tests/test_tools.py -q
```

结果：14 passed。

直接 RAG 查询：

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
from retailcare.policy import rag
from retailcare.tools.impl import search_policy
from retailcare.tools.schema import SearchPolicyIn
print("backend=", rag.backend())
for chunk in search_policy(SearchPolicyIn(query="high value refund human review", k=3)):
    print(chunk.chunk_id, chunk.version, chunk.score, chunk.text)
PY
```

结果显示当前 backend 是 Chroma，并命中：

```text
RET-003 2026.06 High-value refunds: any refund of 200 USD or more requires manual review...
```

## 面试总表达

RetailCare 的 RAG 是面向售后政策的证据 RAG。资料里说 RAG 的价值是把可更新知识从模型参数中搬到外部存储里，生成或决策时按需检索。我的项目把退货、退款、补偿、物流异常等规则拆成带 chunk_id 和 version 的政策块，通过 Chroma 检索，失败时降级到词法检索。它没有做复杂的混合检索和重排，因为当前政策库小、规则边界清楚；我优先做了版本化、fallback、guardrails 和 eval。消融实验显示 policy RAG 和 prompt 内嵌政策成功率接近，但 RAG 的一致性更好，而且解耦了政策更新。因此这个 RAG 的重点不是“大而全”，而是让高风险售后动作有可检索、可引用、可审计、可评测的政策依据。

## 下一章连接

第 4 章进入工具调用。RetailCare 可以重点讲：

- Function Calling schema 如何定义；
- 8 个工具如何分 read/write 风险等级；
- `search_policy` 如何作为普通工具接入 Agent；
- MCP 如何复用同一套工具实现；
- 工具错误、重试、幂等和安全边界如何设计。
