# RetailCare Orchestrator

> Evaluation-driven reliability system for high-risk, multi-turn **e-commerce after-sales** agents.
> Handles 5 intents (order / shipping / **returns-refunds (hero)** / coupons-compensation / escalation),
> and proves it is **reliable, compliant, non-over-reaching, recoverable, and regression-guarded**.

**North star:** reliability × evaluability. Hero task = the full refund flow with idempotency,
HITL confirmation, policy RAG, fault-injection recovery, and action-level compliance metrics.

See [`OPERATIONS_MANUAL.md`](OPERATIONS_MANUAL.md) for the authoritative execution plan
(milestones M0–M4, acceptance gates, anti-dead-end protocol) and
[`RetailCare_Orchestrator_项目定义_v1.md`](RetailCare_Orchestrator_项目定义_v1.md) for the project definition.

## Stack

Python 3.12+ (verified on 3.14) · **LangGraph** (state graph / checkpoint / `interrupt()` HITL) ·
**LiteLLM** (multi-model: DeepSeek v4 flash/pro) · **MCP** tool layer · Pydantic contracts ·
**Chroma** policy RAG · **PostgreSQL** (SQLAlchemy; SQLite fallback) · FastAPI + light web UI ·
pytest + eval-regression CI · Docker Compose.

## Quickstart

```bash
make setup                          # venv + pinned deps
cp .env.example .env                # or keep keys in .claude/.env (both git-ignored)
make test                           # unit tests (no network)
make ping                           # real smoke call to DeepSeek v4
```

### Model note (DeepSeek v4 = reasoning model)
`deepseek-v4-flash` / `deepseek-v4-pro` emit reasoning tokens before the answer, so
keep `max_tokens` generous and read `content` (handled in `retailcare.config`).

### Deployment (PostgreSQL + Chroma via Docker)
Requires Docker Desktop. `docker compose up` brings up Postgres + Chroma; the app
connects via `DATABASE_URL` / `CHROMA_HOST`. Without Docker, dev falls back to
SQLite + embedded Chroma (same code, via SQLAlchemy + Chroma persistent client).

## Status
M0 工程地基 — in progress. See the progress board in `OPERATIONS_MANUAL.md` §0.
