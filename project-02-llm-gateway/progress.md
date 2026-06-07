# Progress Log — LLM Gateway

---

## Session 1 — 2026-05-23

**Goal:** Project setup, planning files created

**Done:**
- Read project spec (`project-02-llm-gateway.md`)
- Created `task_plan.md` with all 5 phases
- Created `findings.md` with initial stack research
- Created `progress.md` (this file)
- Created `docs/INDEX.md` — master document index with rollup checklist
- Created `docs/srs/SRS-001-llm-gateway.md` — full requirements with FR/NFR/acceptance criteria
- Created `docs/design/DESIGN-001-architecture.md` — architecture diagram, component breakdown, config schema
- Created `docs/adr/ADR-001-fastapi.md` — framework decision
- Created `docs/adr/ADR-002-state-store.md` — SQLite→Redis migration strategy
- Created `docs/adr/ADR-003-token-counting.md` — tiktoken + reconciliation approach
- Created `docs/adr/ADR-004-team-config.md` — YAML config rationale

**Current phase:** Phase 1 — Core Gateway (complete — pending real end-to-end smoke test)

**Next action:** Configure gateway.yaml, run against a real backend, verify /admin/usage shows token counts

---

## Session 2 — 2026-05-23

**Goal:** Implement gateway phases 1–5

**Done:**

**Phase 1 — Core Gateway:**
- `gateway/main.py` — FastAPI app with async lifespan (config load, DB init, backend init, rate limiter, router)
- `gateway/models.py` — Pydantic request/response models (`ChatCompletionRequest`, `ChatCompletionResponse`, `UsageInfo`)
- `gateway/config.py` — `GatewayConfig` loader from `gateway.yaml`; team config with `monthly_token_budget`, `models_allowed`, `rate_limit_rpm`, `routing_strategy`, `enforcement_mode`
- `gateway/tokens.py` — tiktoken-based prompt token estimator
- `gateway/observability.py` — structured JSON logging (`log_request`), `generate_request_id`, `current_month`
- `gateway/state/sqlite.py` — async SQLite quota store; `init()`, `get_usage()`, `increment()`, `log_request()`, `get_requests()`, `reset()`
- `gateway/routes/chat.py` — `POST /v1/chat/completions`: rate check → quota check → routing → backend call → accounting → metrics. Streaming (`StreamingResponse`) and non-streaming paths. Fallback triggered on `httpx` error when `routing_strategy = "fallback"`. Shadow fire-and-forget via `asyncio.create_task`.
- `gateway/routes/admin.py` — `GET /admin/usage`, `GET /admin/quota`, `POST /admin/reset`
- `gateway/routes/models.py` — `GET /v1/models`
- `gateway/routes/dashboard.py` — spend/trend/quota HTML dashboard
- `gateway/middleware/auth.py` — API key → team config lookup

**Phase 2 — Quota Enforcement:**
- `gateway/quota.py` — all 3 enforcement modes:
  - `hard`: `used >= budget` → `EnforcementAction.BLOCK` → HTTP 429
  - `soft`: `used >= budget` → `EnforcementAction.WARN` → allow + structured log warning
  - `downgrade`: `used >= threshold_pct` → `EnforcementAction.DOWNGRADE` → `backend_override` to cheaper backend
- `gateway/ratelimit.py` — per-team sliding window RPM limiter

**Phase 3 — Observability:**
- `gateway/metrics.py` — Prometheus counter/histogram metrics; `record()` per request, `prometheus_output()` on `GET /metrics`
- Structured JSON log on every request: `request_id`, `team`, `model`, `backend`, `routing_strategy`, `enforcement_action`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `cost_usd`, `quota_used`, `quota_budget`

**Phase 4 — Multi-Backend Routing:**
- `gateway/backends/base.py` — `LLMBackend` abstract interface: `complete()`, `stream()`, `close()`
- `gateway/backends/openai_compat.py` — `OpenAICompatBackend` via `httpx.AsyncClient`; streaming and non-streaming; reads `prompt_tokens`/`completion_tokens` from response usage
- `gateway/router.py` — all 4 routing strategies:
  - `static`: team config → backend name resolution
  - `cost_aware`: picks cheapest backend by `cost_per_1k_prompt + cost_per_1k_completion`
  - `fallback`: primary backend; fallback triggered at request time in chat route on error
  - `shadow`: primary + fire-and-forget shadow backend; comparison logged

**Phase 5 — Vendor Comparison:**
- `findings.md` — Bifrost vs LiteLLM vs custom build comparison on quota enforcement, routing, observability, auth, shadow routing. Shadow routing confirmed as gap in both vendors; custom build is the only implementation with it.

**App initialized:** `gateway.db` created on startup — SQLite schema applied, app has been run.

---

## Test Results

| Date | Test | Result | Notes |
|------|------|--------|-------|
| 2026-05-23 | App startup | PASS | `gateway.db` created, backends initialized, structured startup log |
| 2026-06-06 | Hard quota enforcement (HTTP 429) | **PASS** | `compliance` team, `enforcement_mode: hard`, `monthly_token_budget: 2_000_000`, `tokens_used: 2000001` — see response below |

**Smoke test — 2026-06-06**

Setup: pre-seeded `team_quota` row `(compliance, 2026-06, 2000001)` — one token over the 2M hard limit. Started gateway on port 8765. Command:

```bash
curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST http://localhost:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer co-change-me" \
  -d '{"model": "local", "messages": [{"role": "user", "content": "Hello"}]}'
```

Response:

```
{"detail":{"error":"quota_exceeded","team":"compliance","tokens_used":2000001,"tokens_budget":2000000}}
HTTP_STATUS:429
```

Hard quota enforcement confirmed: request blocked at quota check (`used >= budget`), before any backend call. HTTP 429 with `error: quota_exceeded`, team name, used/budget values in response body.

---

## Files Created / Modified

| File | Action | Session |
|------|--------|---------|
| task_plan.md | created | 1 |
| findings.md | created | 1 |
| progress.md | created | 1 |
| docs/INDEX.md | created | 1 |
| docs/srs/SRS-001-llm-gateway.md | created | 1 |
| docs/design/DESIGN-001-architecture.md | created | 1 |
| docs/adr/ADR-001-fastapi.md | created | 1 |
| docs/adr/ADR-002-state-store.md | created | 1 |
| docs/adr/ADR-003-token-counting.md | created | 1 |
| docs/adr/ADR-004-team-config.md | created | 1 |
| gateway/\_\_init\_\_.py | created | 2 |
| gateway/main.py | created | 2 |
| gateway/config.py | created | 2 |
| gateway/models.py | created | 2 |
| gateway/tokens.py | created | 2 |
| gateway/observability.py | created | 2 |
| gateway/quota.py | created | 2 |
| gateway/ratelimit.py | created | 2 |
| gateway/metrics.py | created | 2 |
| gateway/router.py | created | 2 |
| gateway/backends/base.py | created | 2 |
| gateway/backends/openai_compat.py | created | 2 |
| gateway/middleware/auth.py | created | 2 |
| gateway/routes/chat.py | created | 2 |
| gateway/routes/admin.py | created | 2 |
| gateway/routes/models.py | created | 2 |
| gateway/routes/dashboard.py | created | 2 |
| gateway/state/base.py | created | 2 |
| gateway/state/sqlite.py | created | 2 |
| gateway.yaml | created | 2 |
| gateway.yaml.example | created | 2 |
| gateway.db | created (on startup) | 2 |
| pyproject.toml | created | 2 |
