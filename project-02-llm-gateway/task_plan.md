# Task Plan — LLM Gateway / Cost Governance

**Goal:** Build lightweight Python LLM gateway with multi-backend routing, per-team quota enforcement, structured logging, cost dashboard, and vendor comparison doc.

**Started:** 2026-05-23  
**Target:** 10 days

---

## Phases

### Phase 1 — Core Gateway (Days 1–3)
**Status:** `in_progress`

Stack: FastAPI + tiktoken + Redis/SQLite + YAML config

Routes:
- `POST /v1/chat/completions`
- `GET /v1/models`
- `GET /admin/usage`
- `GET /admin/quota`
- `POST /admin/reset`

Request lifecycle: auth → quota check → token estimate → route → stream → accounting → metrics

**Start here:** FastAPI app → single `/v1/chat/completions` → proxy one backend → log token counts → write to SQLite

---

### Phase 2 — Quota Enforcement (Days 4–5)
**Status:** `not_started`

YAML team config: api_key, monthly_token_budget, models_allowed, rate_limit_rpm

Enforcement modes (configurable per team):
- Hard block → HTTP 429
- Soft cap → allow + warn metric
- Downgrade → route to cheaper/local model

Quota reset: monthly calendar boundary, carry-over option (2x cap), manual override

---

### Phase 3 — Observability (Days 6–7)
**Status:** `not_started`

Metrics: request.count, tokens.prompt, tokens.completion, latency.ms, quota.pct_used, quota.remaining, errors.count
Tags: team, model, status

Structured JSON logs: timestamp, request_id, team, model, prompt/completion/total tokens, latency_ms, status, quota_remaining

Dashboard (Grafana/Datadog/static HTML):
- Monthly spend by team (tokens × cost-per-token)
- Daily trend
- Model distribution
- Teams at 80%+ quota → alert

---

### Phase 4 — Multi-Backend Routing (Days 8–9)
**Status:** `not_started`

Backend interface: `LLMBackend.complete(messages, model, **kwargs) -> CompletionResponse`

Adapters: BedrockBackend, LlamaCppBackend, OpenAICompatBackend

Routing strategies:
- Static → team config maps to backend
- Cost-aware → cheapest backend that satisfies request
- Fallback → primary + fallback on error/timeout
- Shadow → dual send, compare, return primary (model eval)

---

### Phase 5 — Vendor Comparison Doc (Day 10)
**Status:** `not_started`

Compare: your build vs. Bifrost vs. LiteLLM

Dimensions: quota enforcement, multi-backend routing, observability depth, operational overhead, enterprise auth (OIDC/SAML), audit logging, cost to operate

---

## Deliverables

- [ ] Gateway with 2+ model backends wired
- [ ] Per-team quota enforcement (all 3 modes)
- [ ] Cost dashboard (spend, trends, quota status)
- [ ] Structured logging + metrics emission
- [ ] Demo: team hitting quota limit
- [ ] Comparison doc: your build vs. Bifrost vs. LiteLLM

---

## Decisions Log

| Decision | Rationale | Date |
|----------|-----------|------|
| SQLite first, Redis later | Start simple, upgrade when quota enforcement needs atomic ops | 2026-05-23 |

---

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |
