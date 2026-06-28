# RetailCare Orchestrator

> Evaluation-driven, **state-grounded and security-hardened** ReAct agent for high-risk,
> multi-turn **e-commerce after-sales**. Handles 5 intents (order / shipping /
> **returns-refunds (hero)** / coupons-compensation / escalation) and proves it is
> **reliable, compliant, non-over-reaching, recoverable, and regression-guarded**.

**North star:** reliability × evaluability × **controllability/safety**. Hero task = the full
refund flow with idempotency, HITL confirmation, policy RAG, fault-injection recovery, and
action-level compliance metrics.

## Core doctrine

A deliberately *restrained* design — one ReAct agent over a typed tool layer, governed by
LangGraph state, with safety enforced by the system, not the model:

- **ReAct = business engine** — the agent decides the next action and can switch business
  mid-conversation (no rigid workflow).
- **LangGraph state = control** — structured working memory (intent / focus / findings /
  status) keeps the agent grounded over long, business-switching conversations; a one-shot
  **state digest** is re-rendered each turn and never accumulates in history.
- **System-enforced safety** — a model tool call is a *proposal*, never final authority.
  Identity, idempotency, and high-risk writes are decided in code (schemas, ownership,
  policy, guardrails, HITL, audit).

Details: [`ARCHITECTURE.md`](ARCHITECTURE.md) · policy [`BUSINESS_RULES.md`](BUSINESS_RULES.md).

## Controllability & security upgrade (A → B → C)

A three-phase hardening that closes the gaps between the doctrine above and the code:

| Phase | Theme | Highlights |
|---|---|---|
| **A** | Trust boundary | Identity (`user_id`) is **session-injected**, removed from tool schemas → closes cross-user IDOR; **system-derived idempotency keys** (amount-normalized) stop compensation double-spend; API identity from **bearer/JWT**, `/trace` ownership-gated. |
| **B** | Structured state | Expanded `AgentState` + merge reducer; **fact-source / digest separation** with per-turn re-render (anti-amnesia, no stale snapshots); single-source HITL gating. |
| **C** | Robustness & audit | **HITL hardening** (one write gated per run + action-token binding, fail-closed); injectable clock; per-user cumulative compensation cap; **durable trace** (per `thread_id`, survives restart); WAL + busy_timeout concurrency; production JWT (anti alg-confusion) + MCP identity binding. |

> An independent adversarial QA agent reviewed the upgrade and caught a real
> compensation double-spend (int/float idempotency-key collision), now fixed + regression-tested.

## Stack

Python 3.12+ (verified on 3.14) · **LangGraph** (state graph / checkpoint / `interrupt()` HITL) ·
**LiteLLM** (multi-model: DeepSeek v4 flash/pro) · **MCP** tool layer · Pydantic contracts ·
**Chroma** policy RAG · **PostgreSQL** (SQLAlchemy; SQLite fallback) · FastAPI + light web UI ·
pytest + eval-regression CI · Docker Compose.

## Results

Eval numbers below are the **pre-upgrade M1–M4 baseline** (DeepSeek v4-flash); datasets are
now aligned to the upgraded architecture and a rerun is pending. The A/B/C upgrade is covered
by **93 unit tests + a 12-case model-free regression gate** (both green).

- **Reliability**: self-built 32-task refund eval, runs=3 → **pass^1 0.948 / pass^2 0.906 / pass^3 0.875** (CI95 0.884–0.978), **policy-violation-rate 0**, escalation-precision 1.0, **$0.0017/task**.
- **Ablation (hardening pays off, no new agent)**: L0 pass@1 0.633 → **L1 (guardrails) 0.80** → **L1+RAG 0.833**; tool-selection errors 11→6→5.
- **Safety**: idempotent refunds, HITL confirmation, cross-session resume, fault-injection recovery, model-free **regression CI** (verified to catch an injected policy regression).

See [`reports/`](reports/) for `baseline_report.md`, `ablation_report.md`, `error_taxonomy.md`, `bfcl_report.md`, `pareto_report.md` (each marked as pre-upgrade baseline).

## Quickstart

```bash
make setup                          # venv + pinned deps (Python 3.12 or 3.14)
cp .env.example .env                # or keep keys in .claude/.env (both git-ignored)
make test                           # unit tests + model-free regression gate (no network)
make ping                           # real smoke call to DeepSeek v4
make demo                           # refund hero flow: HITL confirm + cross-session resume
make eval                           # eval closed loop -> pass^k + CI + compliance + taxonomy
make serve                          # FastAPI + web UI at http://127.0.0.1:8000  (chat + live trace)
```

Experiments: `python -m eval.experiments.run_ablations 3` (E1/E3),
`python -m eval.experiments.pareto 2` (E6 quality×cost), `python -m eval.bfcl` (tool accuracy).

### Auth (API)
Identity comes from `Authorization: Bearer <token>`, never the request body. Demo scheme:
`Bearer demo-<user_id>`. Set `RETAILCARE_JWT_SECRET` to switch to HS256 JWT verification.

### Model note (DeepSeek v4 = reasoning model)
`deepseek-v4-flash` / `deepseek-v4-pro` emit reasoning tokens before the answer, so
keep `max_tokens` generous and read `content` (handled in `retailcare.config`).

### Deployment (PostgreSQL + Chroma via Docker)
Requires Docker Desktop. `docker compose up` brings up Postgres + Chroma; the app
connects via `DATABASE_URL` / `CHROMA_HOST`. Without Docker, dev falls back to
SQLite + embedded Chroma (same code, via SQLAlchemy + Chroma persistent client).

## Repository layout

```
src/retailcare/      agent (graph/) · tools (registry/impl/schema) · policy (RAG+store)
                     · api (FastAPI+auth) · mcp_server · trace · memory · clock · config
tests/               93 unit tests (no network)
eval/                harness + datasets/ (bfcl_style, refund_tasks, security_tasks)
reports/             evaluation reports (pre-upgrade baseline)
web/                 single-file chat + live trace UI
ARCHITECTURE.md · BUSINESS_RULES.md   top-level design & policy
```
