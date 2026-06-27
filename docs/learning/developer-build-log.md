# RetailCare 从 0 搭建开发者教学笔记

本文件用“项目作者开发日志”的方式，复盘 RetailCare 这样一个 Agent
工程项目如何从 0 长出来。

它不是普通源码阅读笔记，而是按真实开发思路组织：

```text
1. 项目目标是什么？
2. 因此我需要什么？
3. 我现在写个什么？
4. 代码展示
5. 解释代码
6. 下一步干什么？
```

阅读目标：站在开发者视角，理解每一步为什么存在、为什么先写它、它如何服务后面的
Agent / Tool / Guardrail / Eval。

## 总开发路线

真实开发一个类似 RetailCare 的 Agent 项目，比较合理的顺序不是一上来写
LangGraph，而是先把业务、工程地基、工具层、Agent 层、可靠性层逐步搭起来。

```text
00. 明确项目目标和可靠性标准
01. 搭 Python 项目骨架
02. 建配置系统
03. 建业务数据模型
04. 写 seed 数据
05. 写第一个无模型测试
06. 写工具 schema 和工具实现
07. 写工具 registry
08. 接入 LLM tool calling
09. 建 ReAct / LangGraph 循环
10. 加 guardrails
11. 加 HITL confirmation
12. 加 checkpoint / resume
13. 加 trace / summary memory
14. 加 eval harness
15. 加 API / CLI / Web UI
16. 加 MCP 暴露工具
17. 写报告、操作手册、部署文件
```

第一轮学习不要求一次把 00-17 全部吃透。我们先按这个顺序走一遍骨架，
之后再回到每个模块深挖。

---

## 00. 明确项目目标和可靠性标准

### 1. 项目目标是什么？

我要做的不是一个普通聊天机器人，而是一个面向电商售后/客服场景的
Agent 系统。

它需要处理：

- 订单查询；
- 物流查询；
- 退货退款；
- 优惠券和补偿；
- 投诉升级；
- 多轮对话；
- 高风险写操作，例如退款、补偿、人工升级。

更重要的是，这个系统不能只是“看起来会聊天”。它必须可追踪、可评测、
可恢复、可合规。

所以项目目标可以压缩成一句话：

```text
构建一个面向电商售后的可靠 Agent 系统，让它能调用工具处理真实业务，
并用规则、人工确认、追踪和评测证明它没有乱来。
```

### 2. 因此我需要什么？

如果目标是“可靠客服 Agent”，那我至少需要这些能力：

| 需求 | 为什么需要 |
|---|---|
| 业务规则 | 退款/补偿不能靠模型自由发挥 |
| 订单/物流/优惠券数据 | Agent 必须查真实数据，而不是编答案 |
| 工具层 | 模型通过工具读取或改变业务状态 |
| 状态管理 | 多轮对话需要知道之前发生了什么 |
| 高风险控制 | 写操作要确认、阻断或升级人工 |
| 追踪日志 | 出错后要知道模型调用了什么工具 |
| 评测集 | 不能只靠 demo，要量化成功率 |
| 回归测试 | 改代码后不能把安全规则改坏 |
| API/CLI | 项目要能被人实际运行和演示 |

这一步非常关键：它决定了后面的架构不是“多 Agent 炫技”，而是围绕可靠性展开。

### 3. 我现在写个什么？

第一步先写项目定义文档和架构原则，而不是代码。

在当前项目中，对应文件是：

- `RetailCare_Orchestrator_项目定义_v1.md`
- `README.md`
- `ARCHITECTURE.md`
- `BUSINESS_RULES.md`
- `OPERATIONS_MANUAL.md`

这些文件回答：

- 这个项目要解决什么业务问题？
- 为什么退款是 hero task？
- 为什么当前选择单 Agent，而不是多 Agent？
- 哪些规则必须代码强制？
- 如何证明系统可靠？

### 4. 代码展示

这一阶段主要不是代码，而是“项目契约”。例如 `BUSINESS_RULES.md` 中的核心规则：

```text
Every write operation must pass:

1. Parameter completeness
2. Policy check
3. Confirmation or escalation
4. Idempotency
5. Audit
```

对应中文理解：

```text
每个高风险写操作都必须：
1. 参数完整；
2. 查业务规则；
3. 该确认就确认，该升级人工就升级；
4. 保证重复执行不会重复退款；
5. 留审计记录。
```

### 5. 解释代码 / 文档思想

这里最重要的思想是：

```text
先定义风险边界，再写 Agent。
```

很多初学者会先写：

```text
用户输入 -> LLM -> 回答
```

但真实业务里这样不够。因为客服 Agent 可能会触发退款、补偿、投诉升级。
这些动作会改变真实世界状态，所以必须有业务规则和审计。

因此，RetailCare 的开发顺序应该是：

```text
业务目标
-> 风险规则
-> 数据模型
-> 工具层
-> Agent 编排
-> 评测和观测
```

不是：

```text
先找一个 Agent 框架
-> 拼几个工具
-> 再想怎么防止出错
```

### 6. 下一步干什么？

下一步不是直接写 Agent，而是搭工程骨架：

```text
Python 包结构
依赖文件
测试配置
Makefile
环境变量模板
```

因为如果项目连稳定运行和测试都做不到，后面的 Agent 逻辑会越来越难调。

---

## 01. 搭 Python 项目骨架

### 1. 项目目标是什么？

现在我要让这个想法变成一个可以运行、可以测试、可以继续扩展的 Python 项目。

这一阶段的目标是：

```text
让项目具备最基本的工程形态：
能安装依赖、能 import 包、能跑测试、能统一执行常用命令。
```

### 2. 因此我需要什么？

我需要：

- 一个 Python package；
- 一个依赖清单；
- 一个测试配置；
- 一个统一命令入口；
- 一个版本号；
- 一个最小 smoke test。

对应文件：

```text
pyproject.toml
requirements.txt
Makefile
src/retailcare/__init__.py
tests/test_smoke.py
```

### 3. 我现在写个什么？

先写项目结构：

```text
RetailCare Orchestrator/
  pyproject.toml
  requirements.txt
  Makefile
  src/
    retailcare/
      __init__.py
  tests/
    test_smoke.py
```

这个结构的思想是：正式包代码放在 `src/retailcare/`，测试放在 `tests/`。

### 4. 代码展示

`pyproject.toml` 的关键部分：

```toml
[project]
name = "retailcare-orchestrator"
version = "0.1.0"
description = "Evaluation-driven reliability system for high-risk multi-turn e-commerce after-sales agents."
requires-python = ">=3.11"
readme = "README.md"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q"
```

`src/retailcare/__init__.py`：

```python
"""RetailCare Orchestrator — evaluation-driven reliability system for e-commerce after-sales agents."""

__version__ = "0.1.0"
```

`Makefile` 的关键命令：

```makefile
test:
	PYTHONPATH=src .venv/bin/python -m pytest

serve:
	.venv/bin/uvicorn retailcare.api.app:app --reload --app-dir src

demo:
	PYTHONPATH=src .venv/bin/python -m retailcare.demo
```

`tests/test_smoke.py` 里的最小测试：

```python
from retailcare import __version__


def test_version():
    assert __version__
```

### 5. 解释代码

#### 为什么用 `src/retailcare/`？

这是 Python 项目里常见的 `src layout`。

它的好处是：测试时必须像真实用户一样 import 你的包，而不是不小心 import
当前目录里的临时文件。

简单理解：

```text
src/retailcare 是正式产品代码
tests 是验证产品代码的地方
learning_lab 是学习实验区
```

#### `pyproject.toml` 在干什么？

它告诉 Python 工具：

- 项目叫什么；
- 支持什么 Python 版本；
- 包在哪里；
- pytest 应该从哪里找测试；
- 测试时如何找到 `src/retailcare`。

这一行尤其重要：

```toml
pythonpath = ["src"]
```

它让测试可以这样写：

```python
from retailcare import __version__
```

而不是写一堆相对路径。

#### `requirements.txt` 在干什么？

它固定依赖版本，例如：

```text
fastapi
sqlalchemy
pydantic
langgraph
litellm
pytest
ruff
```

这让项目可以复现：

```text
同一份代码 + 同一组依赖版本 = 尽量一致的运行结果
```

Agent 项目尤其需要固定依赖，因为框架变化很快。

#### `Makefile` 在干什么？

它把常用命令变成固定入口：

```text
make test
make demo
make serve
make eval
```

这样开发者不用每次记复杂命令。

在团队项目里，Makefile 的价值是：

```text
降低运行成本，统一操作方式。
```

#### `test_smoke.py` 为什么这么简单？

因为第一步只需要确认：

```text
项目包能被 import。
测试系统能跑。
基本配置没有炸。
```

这叫 smoke test。它不是深度测试，只是确认“系统冒烟但没有起火”。

### 6. 下一步干什么？

现在项目已经能作为 Python 包运行。下一步要做配置系统：

```text
模型 API 地址
模型名称
API key
数据库地址
Chroma 配置
价格配置
```

这些东西不能写死在代码里，所以要进入下一步：

```text
02. 建配置系统：config.py + .env.example
```

---

## 当前手把手路线

接下来我们会继续按这个开发日志往下走：

```text
02. 建配置系统
03. 建业务数据模型
04. 写 seed 数据
05. 写第一个工具
06. 把工具接到 Agent
```

每一步都按同样结构：

```text
目标 -> 需求 -> 写什么 -> 代码 -> 解释 -> 下一步
```

---

## 02. 建配置系统

### 1. 项目目标是什么？

现在项目已经能作为 Python 包运行，下一步要解决的是：

```text
不同环境下，模型、数据库、价格、RAG 存储路径这些配置从哪里来？
```

Agent 项目和普通脚本最大的不同之一是：它通常会连接很多外部系统。

例如 RetailCare 需要：

- LLM API 地址；
- LLM API key；
- 默认模型；
- strong / weak 模型；
- token 价格；
- 数据库地址；
- Chroma/RAG 存储路径；
- 测试、开发、生产环境的不同配置。

这些东西不能散落在业务代码里，更不能把密钥直接写死。

### 2. 因此我需要什么？

我需要一个集中配置层：

```text
.env.example         告诉开发者需要哪些环境变量
.env / .claude/.env  放真实本地配置，不能提交
config.py            读取配置，给项目其他模块统一使用
Settings             结构化保存配置
```

这一层要满足：

| 需求 | 原因 |
|---|---|
| 默认值 | 没有 `.env` 时项目也能跑基础测试 |
| 环境变量覆盖 | 本地、CI、生产可以用不同设置 |
| 不泄露密钥 | API key 不能提交到仓库 |
| 可测试 | 配置错误要尽早暴露 |
| 可观测 | 能知道当前用的模型、数据库和价格设置 |

### 3. 我现在写个什么？

先写两个文件：

```text
.env.example
src/retailcare/config.py
```

`.env.example` 是给人的说明。

`config.py` 是给代码用的统一配置入口。

### 4. 代码展示

`.env.example` 的关键内容：

```dotenv
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

RETAILCARE_MODEL_WEAK=deepseek-v4-flash
RETAILCARE_MODEL_STRONG=deepseek-v4-pro

RETAILCARE_MAX_TOKENS=2048
RETAILCARE_TEMPERATURE=0.0

RETAILCARE_PRICE_IN_PER_M=0.28
RETAILCARE_PRICE_OUT_PER_M=0.42

DATABASE_URL=postgresql+psycopg2://retailcare:retailcare@localhost:5432/retailcare
# DATABASE_URL=sqlite:///./retailcare.db

CHROMA_PERSIST_DIR=./.chroma
```

`config.py` 的核心结构：

```python
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(_ROOT / ".claude" / ".env", override=False)
load_dotenv(_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "deepseek-v4-flash")
    model_weak: str = os.getenv("RETAILCARE_MODEL_WEAK", "deepseek-v4-flash")
    model_strong: str = os.getenv("RETAILCARE_MODEL_STRONG", "deepseek-v4-pro")
    max_tokens: int = int(os.getenv("RETAILCARE_MAX_TOKENS", "2048"))
    temperature: float = field(default_factory=lambda: _f("RETAILCARE_TEMPERATURE", 0.0))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./retailcare.db")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./.chroma")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


settings = Settings()
```

项目还定义了一个 `LLMResult`，用于记录模型输出、token 和成本：

```python
@dataclass
class LLMResult:
    content: str
    reasoning: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float

    def cost_usd(self, s: Settings = settings) -> float:
        return (
            self.prompt_tokens / 1_000_000 * s.price_in_per_m
            + self.completion_tokens / 1_000_000 * s.price_out_per_m
        )
```

### 5. 解释代码

#### 为什么先读 `.claude/.env`，再读 `.env`？

当前项目中：

```python
load_dotenv(_ROOT / ".claude" / ".env", override=False)
load_dotenv(_ROOT / ".env", override=False)
```

含义是：

```text
优先尝试读取 .claude/.env
再尝试读取项目根目录 .env
但 override=False 表示不要覆盖已经存在的环境变量
```

这样做的好处是：

- 可以把真实 key 放在 `.claude/.env`；
- 也可以用项目根目录 `.env`；
- CI 或 shell 里已经设置好的环境变量不会被文件覆盖。

#### 为什么 `Settings` 用 dataclass？

因为配置是一组结构化字段。

写成 dataclass 后，代码里可以这样用：

```python
from retailcare.config import settings

print(settings.model)
print(settings.database_url)
```

比到处写：

```python
os.getenv("OPENAI_MODEL")
```

更统一、更容易测试。

#### 为什么要有默认值？

例如：

```python
database_url: str = os.getenv("DATABASE_URL", "sqlite:///./retailcare.db")
```

如果没有配置数据库，项目默认用 SQLite。

这让本地开发和测试更轻：

```text
没有 Docker / Postgres 也能跑测试。
```

#### 为什么要记录 token 成本？

Agent 项目不只关心能不能回答，还关心：

```text
每个任务花了多少钱？
弱模型够不够？
强模型提升是否值得？
```

所以 `LLMResult.cost_usd()` 会根据 token 和单价计算成本。后面的 eval
harness 会用这个结果计算 cost/task。

### 6. 输入输出 / 怎么运行

#### 运行配置模块

输入命令：

```bash
PYTHONPATH=src .venv/bin/python -m retailcare.config
```

本次实际输出：

```text
base_url=https://api.deepseek.com model=deepseek-v4-flash strong=deepseek-v4-pro weak=deepseek-v4-flash configured=True db=sqlite:///./retailcare.db
```

怎么看成功？

```text
退出码是 0
能打印 base_url / model / strong / weak / configured / db
没有 ImportError
没有环境变量解析异常
没有把 API key 明文打印出来
```

怎么看失败？

常见失败形式：

```text
ModuleNotFoundError: No module named 'retailcare'
```

说明大概率忘了设置 `PYTHONPATH=src`，或者虚拟环境/包结构没配好。

```text
ValueError: invalid literal for int()
```

说明类似 `RETAILCARE_MAX_TOKENS` 这种本应是数字的环境变量写错了。

```text
configured=False
```

不一定是失败。它只表示当前没有配置真实 API key。无网络测试仍然可以跑，
但 `make ping` 或真实 LLM demo 会失败。

#### 运行 smoke test

输入命令：

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_smoke.py -q
```

本次实际输出：

```text
...                                                                      [100%]
```

三个点代表三个测试都通过。

对应测试内容：

```python
def test_version():
    assert __version__


def test_settings_defaults():
    s = Settings()
    assert s.base_url.startswith("http")
    assert s.model
    assert s.model_strong and s.model_weak


def test_cost_computation():
    r = LLMResult(
        content="ok", reasoning="", model="x",
        prompt_tokens=1_000_000, completion_tokens=1_000_000, latency_s=0.1,
    )
    expected = settings.price_in_per_m + settings.price_out_per_m
    assert abs(r.cost_usd() - expected) < 1e-9
```

怎么看成功？

```text
输出里有 [100%]
没有 FAILED
没有 ERROR
命令退出码是 0
```

怎么看失败？

如果 `test_settings_defaults` 失败，说明默认配置不完整。

如果 `test_cost_computation` 失败，说明成本计算逻辑不对，后面 eval 的
cost/task 指标就不可信。

如果 `test_version` 失败，说明包最小导入或版本定义就有问题。

### 7. 这一节掌握到什么程度算过关？

你能回答下面问题，就算本节过关：

- `.env.example` 和 `.env` 的区别是什么？
- 为什么真实 API key 不能写进代码？
- `Settings` 在项目里起什么作用？
- 为什么项目默认用 SQLite？
- `configured=False` 一定是错误吗？
- `LLMResult.cost_usd()` 为什么对 eval 有用？
- 如何用一个命令验证配置模块能正常加载？
- 如何看 pytest 输出是成功还是失败？

### 8. 下一步干什么？

配置系统之后，下一步要建立业务数据模型。

因为 Agent 不能只凭语言回答售后问题，它必须能查：

```text
订单
商品
物流
优惠券
退款工单
补偿记录
审计日志
```

所以接下来进入：

```text
03. 建业务数据模型：data/models.py
```

---

## 2026-06-21 工程审查修正：从“能跑”到“更真实”

这次根据资料第 4、8、9 章重新审查项目，重点看：

```text
工具 schema 是否真实
高风险写操作是否有权限和两步授权
Prompt 注入是否有防御
Docker 部署是否能复现
```

发现并修正了几个“面试容易被问穿”的问题：

| 问题 | 为什么不真实 | 修正 |
|---|---|---|
| 订单工具不带 `user_id` | 用户只要知道 `order_id` 就可能查或退别人的订单 | `get_order`、`get_shipment`、`check_return_eligibility`、`create_return_request` schema 增加 `user_id`，后端校验 order ownership |
| MCP 入口没有同步权限字段 | MCP 可绕过 Agent prompt 的用户隔离 | MCP 工具签名同步增加 `user_id` |
| RAG Docker 服务没接上 | compose 有 Chroma，但代码一直用内存 Chroma | `CHROMA_HOST` 存在时使用 `chromadb.HttpClient`，否则本地 persistent Chroma |
| Docker 镜像缺少 `web/` | 容器 `/` 首页可能找不到静态页面 | Dockerfile 复制 `web/` |
| Compose 依赖本机 `.claude/.env` | 换机器可能起不来 | 改为环境变量默认值，不硬依赖本地 secret 文件 |
| Chroma 宿主端口固定 8000 | 容易和本地服务冲突 | `CHROMA_HOST_PORT` 默认 8001，容器内仍用 8000 |
| Chroma 镜像使用 `latest` | 部署不可复现 | 固定为 `chromadb/chroma:1.5.9`，与 Python 依赖版本一致 |
| FastAPI startup 用 deprecated API | 测试有 deprecation warning | 改为 lifespan，并加 `RETAILCARE_SEED_ON_STARTUP` |
| 仓库有 `db 2.py` / `models 2.py` | 明显误复制文件 | 删除重复文件 |

验证结果：

```text
make test
49 passed
baseline held — 12 safety decisions correct

ruff check src tests eval
All checks passed!

docker compose --profile full up -d --build
app healthy
GET /health -> {"ok": true}
GET / -> 返回 Web UI HTML
Chroma heartbeat -> OK
容器内 RAG backend -> chroma-http:chroma:8000
```

这轮修正的设计思路是：

```text
Prompt 告诉模型要带 user_id
Schema 强制 user_id 成为必填参数
工具实现校验 user_id 是否真的拥有 order_id
Guardrail 在写操作前再次检查
MCP 和 Docker 部署路径同步这些约束
```

这比“只在 Prompt 里说不要越权”更真实，也更符合资料里提到的工具权限控制、参数校验、两步授权、审计和可部署性要求。
