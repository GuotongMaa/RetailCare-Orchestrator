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

## Results (DeepSeek v4-flash)

- **Reliability**: self-built 32-task refund eval, runs=3 → **pass^1 0.948 / pass^2 0.906 / pass^3 0.875** (CI95 0.884–0.978), **policy-violation-rate 0**, escalation-precision 1.0, **$0.0017/task**.
- **Ablation (hardening pays off, no new agent)**: L0 pass@1 0.633 → **L1 (guardrails) 0.80** → **L1+RAG 0.833**; tool-selection errors 11→6→5.
- **Safety**: idempotent refunds, HITL confirmation, cross-session resume, fault-injection recovery, model-free **regression CI** (verified to catch an injected policy regression).

See `reports/` for `baseline_report.md`, `ablation_report.md`, `error_taxonomy.md`, `bfcl_report.md`, `pareto_report.md`.

## Quickstart

```bash
make setup                          # venv + pinned deps (Python 3.12 or 3.14)
cp .env.example .env                # or keep keys in .claude/.env (both git-ignored)
make test                           # unit tests (no network)
make ping                           # real smoke call to DeepSeek v4
make demo                           # refund hero flow: HITL confirm + cross-session resume
make eval                           # eval closed loop -> pass^k + CI + compliance + taxonomy
make serve                          # FastAPI + web UI at http://127.0.0.1:8000  (chat + live trace)
```

Experiments: `python -m eval.experiments.run_ablations 3` (E1/E3),
`python -m eval.experiments.pareto 2` (E6 quality×cost), `python -m eval.bfcl` (tool accuracy).

### Model note (DeepSeek v4 = reasoning model)
`deepseek-v4-flash` / `deepseek-v4-pro` emit reasoning tokens before the answer, so
keep `max_tokens` generous and read `content` (handled in `retailcare.config`).

### Deployment (PostgreSQL + Chroma via Docker)
Requires Docker Desktop. `docker compose up` brings up Postgres + Chroma; the app
connects via `DATABASE_URL` / `CHROMA_HOST`. Without Docker, dev falls back to
SQLite + embedded Chroma (same code, via SQLAlchemy + Chroma persistent client).

## Status
M0 工程地基 — in progress. See the progress board in `OPERATIONS_MANUAL.md` §0.
