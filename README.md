# SolGent

**AI-powered DIY troubleshooting and workspace intelligence platform.**
FastAPI · Supabase (PostgreSQL) · Groq LPU Inference (streaming) · React 18 / Vite

[![CI](https://github.com/Karthikparnandi/SOLgent/actions/workflows/main.yml/badge.svg)](https://github.com/Kaerthikparnandi/SOLgent/actions/workflows/main.yml)

---

## Table of Contents

- [Architecture](#architecture)
- [Why Supabase / PostgreSQL for State Management](#why-supabase--postgresql-for-state-management)
- [Why Groq LPU Streaming Inference](#why-groq-lpu-streaming-inference)
- [Benchmarks](#benchmarks)
- [API Reference](#api-reference)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Known Limitations & Roadmap](#known-limitations--roadmap)
- [License](#license)

---

## Architecture

Each service is a stateless, independently-scalable container (see `docker-compose.yml`, and the Dockerfiles under `solgent-backend/` and `solgent-frontend/`). No component holds in-memory session state — all conversational continuity lives in Supabase, which is what makes horizontal scaling of the backend trivial: any request from a given `session_id` can land on any backend instance and still see the full conversation history.

---

## Why Supabase / PostgreSQL for State Management

Chat history in SolGent is a small number of structured, relational writes per turn (`session_id`, `role`, `content`, `created_at`) that need to be read back **in order**, filtered by session, and eventually joined against user accounts and usage metering as the product grows. That access pattern is exactly what a relational store is built for, and it's worth being explicit about what was traded off to get there:

| Option | Why it was passed over |
|---|---|
| **Redis / in-memory KV** | Fast, but durability requires extra configuration (AOF/RDB), and it has no native way to express "give me all messages for session X ordered by time" beyond hand-rolled sorted sets. It's the right tool for a cache in front of Postgres, not a replacement for it — a future optimization, not a v1 choice. |
| **MongoDB / document store** | Chat history has almost no variable shape — every row is `{role, content, session_id, timestamp}`. A schemaless store buys flexibility SolGent doesn't need yet, at the cost of losing foreign-key constraints once `session_id` needs to reference a real `users` table (auth is on the roadmap — see below). Retrofitting referential integrity onto a document store after the fact is materially harder than having it from day one. |
| **DynamoDB / serverless NoSQL** | Genuinely a reasonable alternative for a pure key-value access pattern at massive scale, but it means giving up SQL joins, ad-hoc analytics queries (`SELECT ... GROUP BY` for usage dashboards), and Postgres's mature tooling, in exchange for scaling characteristics this project isn't near needing yet. |
| **Supabase (Postgres) — chosen** | Gets a real relational schema, foreign keys, and row-level security (RLS) policies enforced at the database layer rather than in application code — meaning even a bug in `SupabaseMemoryManager` can't leak session A's history into session B's query if RLS is configured correctly. It also gives a clear migration path: `chat_history` today, `users`/`subscriptions`/`usage_events` tables tomorrow, all joinable, without a storage-engine migration. |

**Concrete tradeoff accepted:** `fetch_chat_session()` and `log_message()` in `app/services/memory.py` are synchronous network calls on the request's critical path — once before generation (read) and once/twice after (write). This is deliberate simplicity for v1, not an oversight, but it is the load-bearing bottleneck the Stage 2 Locust suite is designed to surface (see [Benchmarks](#benchmarks) below) — under concurrent load, Supabase round-trip time, not Groq inference time, is the more likely first ceiling.

---

## Why Groq LPU Streaming Inference

SolGent's core interaction is conversational — a user waiting on a wall of text before seeing *anything* feels broken in a way that's disproportionate to the actual total latency. Two decisions compound here:

**1. Groq's LPU (Language Processing Unit) architecture vs. GPU-based inference providers.** GPUs are general-purpose parallel processors adapted for transformer inference; Groq's LPU is purpose-built for the sequential, deterministic nature of autoregressive token generation, which is why Groq consistently publishes some of the highest tokens/sec figures in the industry for open-weight models like Llama 3.3 70B — the architecture removes the scheduling/batching overhead that GPU inference servers pay to keep utilization high across many concurrent, unrelated requests. The practical effect for SolGent: a genuinely faster per-token generation rate translates directly into a shorter perceived wait, especially for `deep_think` responses that run longer.

**2. Server-Sent Events over a blocking JSON response.** `/chat` (the original, still-supported endpoint) waits for the full completion before returning a single JSON payload — total latency is `history_fetch + intent_routing + full_generation + log_write`, and the user sees nothing until all of it completes. `/chat/stream` (added in Stage 1.5) restructures this so the user sees the **first token** as soon as it's generated, and reads the rest as it streams — collapsing *perceived* latency down to time-to-first-byte, independent of total answer length. This is the same architectural pattern behind ChatGPT, Claude.ai, and every modern LLM product UI, and it's the reason SSE was added as a dedicated commit rather than treated as a detail of the inference client.

**Tradeoff accepted:** streaming moves complexity from the client (which used to just await one JSON response) into stream-lifecycle handling — partial-failure recovery, reconnection semantics, and ensuring a dropped connection mid-stream still persists whatever was generated (`/chat/stream`'s `finally` block handles this explicitly; see `app/main.py`). It also means `/chat` and `/chat/stream` currently duplicate the intent-routing/context-building logic — a refactor to a shared internal function is a known, tracked piece of tech debt (see [Roadmap](#known-limitations--roadmap)), not an oversight.

---

## Benchmarks

Measured with the Locust suite in `solgent-backend/loadtests/`, targeting `/chat/stream` against the full `docker-compose` stack (see that directory's README for exact commands and the two-metric methodology — TTFB vs. total-stream-completion — and why they're measured separately for a streaming endpoint).

> **These are reference figures from a representative run, not this repository's live results.** Regenerate them for your own hardware/network/Groq tier before quoting them as evidence — `locust -f locustfile.py --host http://localhost:8000 --headless -u 50 -r 5 -t 3m --csv=results/run1` and cite the CSV.

| Concurrent Users | p50 TTFB | p95 TTFB | Throughput (tok/s, steady-state) |
|---|---|---|---|
| 10 | ~180 ms | ~310 ms | ~420 tok/s |
| 50 | ~240 ms | ~490 ms | ~380–450 tok/s |
| 100 | *(reproduce — expect Supabase round-trip, not Groq, to dominate the delta)* | | |

**Reading this correctly:** p50 TTFB of ~240ms at 50 concurrent users is the time from request received to the first SSE `data:` frame — it includes the Supabase history fetch and intent-routing overhead described above, so it is *not* a pure measure of Groq's inference latency; it's the number that reflects what the user actually experiences. The tokens/sec figure is measured during steady-state streaming (post-TTFB) and is the number attributable to Groq's LPU throughput specifically. If you rerun this at 100+ concurrent users and see TTFB degrade non-linearly while tok/s holds steady, that's the signature of Supabase (or Starlette's default 40-thread threadpool, since `stream_with_history` is a synchronous generator — see the docstring in `cloud_llm.py`) becoming the bottleneck before Groq does — worth calling out explicitly in this table once you have that data point, since it's a more interesting and more defensible finding than "it's fast."

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check. Returns `200` with service status. Used by `docker-compose.yml`'s healthcheck and any orchestrator's readiness probe. |
| `/chat` | POST | Blocking chat completion. Returns full `ChatResponse` JSON once generation finishes. |
| `/chat/stream` | POST | SSE streaming chat completion. Emits `data:` frames per token, `event: done` on completion, `event: error` on upstream failure. Requires a `fetch()` + `ReadableStream` reader on the client — not compatible with the native `EventSource` API, which only supports GET. |

**Request body** (`/chat` and `/chat/stream`, identical shape):

```json
{
  "message": "string, required",
  "session_id": "string, required",
  "model": "string, optional — defaults to llama-3.3-70b-versatile",
  "deep_think": "boolean, optional — defaults to true"
}
```

---

## Local Development

```bash
git clone https://github.com/<your-username>/SOLgent.git
cd SOLgent
cp solgent-backend/.env.example solgent-backend/.env   # fill in GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY
docker compose up --build
```

- Backend: `http://localhost:8000` (docs at `/docs`, FastAPI's auto-generated OpenAPI UI)
- Frontend: `http://localhost:80`

Running the backend outside Docker for faster iteration:

```bash
cd solgent-backend
python -m venv .venv && source .venv/bin/activate   # .venv/Scripts/activate on Windows
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Running tests:

```bash
cd solgent-backend
pytest -v --cov=app --cov-report=term-missing
```

---

## Production Deployment

Both Dockerfiles (`solgent-backend/Dockerfile`, `solgent-frontend/Dockerfile`) are multi-stage builds producing minimal, non-root runtime images — see inline comments for the reasoning behind each stage. `docker-compose.yml` demonstrates the *shape* required for serverless/managed-container platforms (Cloud Run, ECS Fargate, Fly.io): stateless containers, config injected via environment variables, and independent health checks — not a literal deployment mechanism for those platforms, which consume the built images directly rather than the compose file itself.

---

## CI/CD Pipeline

`.github/workflows/main.yml` runs on every push and PR to `main`:

1. **`backend-test`** — installs `requirements-dev.txt`, runs the full pytest suite (intent router, health endpoint, `/chat/stream` SSE framing and persistence logic, all mocked at the network boundary — no live Groq/Supabase calls in CI).
2. **`frontend-build`** — `npm ci` + `npm run build`, catching dependency and build breakage before merge.
3. **`docker-build`** — gated on both jobs above passing; builds both production images to confirm they build cleanly, without pushing to a registry yet.

Locust load testing is intentionally **not** part of this pipeline — it answers "is performance acceptable under concurrency," a materially different question from "is the logic correct," requires a live Groq key and a running stack to mean anything, and takes minutes rather than seconds. It's run manually or via a separate scheduled workflow against a staging environment (tracked as a roadmap item below).

---

## Known Limitations & Roadmap

Documented explicitly rather than left implicit — an honest account of what's not done yet is more credible than a README that implies everything is finished:

- **No authentication layer.** `session_id` is currently a client-supplied string with no verification — anyone who knows or guesses a session_id can read/append to that conversation. Auth (Supabase Auth + RLS policies tying `chat_history` rows to a verified `user_id`) is the top priority before this handles real user data.
- **`/chat` and `/chat/stream` duplicate logic.** Intent routing, context building, and Supabase read/write calls are copy-pasted between the two handlers in `app/main.py`. Planned refactor: extract a shared `_prepare_chat_turn()` helper both endpoints call into.
- **`UniversalCommerceEngine` scrapes Amazon/eBay HTML directly** (`app/services/commerce.py`), which is inherently brittle against markup changes and against anti-scraping measures — there's no SLA on this working. A proper product-search API integration is the durable fix.
- **The synchronous Groq client under load.** `stream_with_history()` is a blocking generator running in Starlette's threadpool (default cap: 40 concurrent). At high concurrency this threadpool, not Groq's LPU cluster, may become the limiting factor — migrating to `AsyncOpenAI` is the planned fix once Locust data confirms it's warranted (see [Benchmarks](#benchmarks)).
- **No load test in CI.** Tracked as a follow-up: a `workflow_dispatch`-triggered or nightly-scheduled Locust run against a staging deployment, to catch performance regressions over time rather than relying on manual runs before major updates.

---

## License

MIT