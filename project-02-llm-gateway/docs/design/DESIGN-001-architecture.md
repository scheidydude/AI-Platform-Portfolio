# DESIGN-001 — System Architecture Overview

**Version:** 0.1 (Draft)  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Draft — update as built

---

## 1. Summary

LLM gateway acts as a reverse proxy between client applications and model backends. It enforces per-team token budgets, routes to the appropriate backend, and emits structured observability data on every request.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│   (any OpenAI-compatible client: curl, Python SDK, app code)    │
└───────────────────────────┬─────────────────────────────────────┘
                            │  POST /v1/chat/completions
                            │  Authorization: Bearer <api-key>
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Gateway (FastAPI)                          │
│                                                                 │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐ │
│  │ Auth         │→ │ Quota Check   │→ │ Token Estimator      │ │
│  │ Middleware   │  │ Middleware    │  │ (tiktoken)           │ │
│  │ key→team     │  │ hard/soft/    │  │ pre-request estimate │ │
│  └──────────────┘  │ downgrade     │  └──────────────────────┘ │
│                    └───────────────┘           │                │
│                                                ▼                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Router                               │   │
│  │  static | cost-aware | fallback | shadow                │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │   Bedrock    │   │  llama.cpp   │   │ OpenAI-compat│
   │  (boto3)     │   │  (HTTP)      │   │  (HTTP)      │
   └──────────────┘   └──────────────┘   └──────────────┘
           │                   │                   │
           └───────────────────┴───────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Post-Request Accounting                       │
│   actual tokens ← response headers                             │
│   reconcile with estimate → log discrepancy                    │
│   UPDATE quota in state store                                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
   ┌──────────────┐       ┌──────────────┐
   │ State Store  │       │  Observability│
   │ SQLite/Redis │       │  JSON logs   │
   │ quota counts │       │  Metrics     │
   └──────────────┘       │  (Datadog/   │
                          │  Prometheus) │
                          └──────────────┘
```

---

## 3. Component Responsibilities

### 3.1 Auth Middleware

- Reads `Authorization: Bearer <key>` header
- Looks up key in loaded team config (YAML)
- Attaches `team` identity to request context
- Returns HTTP 401 for unknown keys

### 3.2 Quota Check Middleware

- Reads current usage for team from state store
- Applies enforcement mode (hard block / soft cap / downgrade)
- Hard block: return HTTP 429 if `used >= budget`
- Soft cap: proceed + set flag to emit warning metric
- Downgrade: swap backend to cheaper model if `used >= threshold`
- Executes before token estimation to fail-fast

### 3.3 Token Estimator

- Uses tiktoken (`cl100k_base`) on request messages
- Stores estimate in request context
- Used for pre-flight budget headroom check
- Actual tokens from response reconciled post-request

### 3.4 Router

Four strategies (configurable per team in YAML):

| Strategy | Behavior |
|----------|----------|
| Static | Team config directly maps to one backend |
| Cost-aware | Compare cost-per-token across eligible backends, pick cheapest |
| Fallback | Try primary; on error/timeout, try secondary |
| Shadow | Send to primary and shadow in parallel; return primary; log both responses |

### 3.5 Backend Adapters

Common interface:

```python
class LLMBackend:
    async def complete(
        self, messages: list[dict], model: str, **kwargs
    ) -> CompletionResponse:
        ...
```

Adapters: `BedrockBackend`, `LlamaCppBackend`, `OpenAICompatBackend`

### 3.6 Post-Request Accounting

- Extract actual `prompt_tokens` / `completion_tokens` from response
- INCR quota counter in state store (atomic in Redis, single-writer lock in SQLite)
- Compute and log discrepancy between tiktoken estimate and actual

### 3.7 State Store

Phase 1: SQLite  
Phase 2+: Redis (atomic INCR, no race conditions under concurrency)

See [ADR-002](../adr/ADR-002-state-store.md) for rationale.

Schema (logical, maps to either):

```
team_quota:
  team_id       TEXT PRIMARY KEY
  month         TEXT              -- "2026-05"
  tokens_used   INTEGER
  tokens_budget INTEGER
  enforcement   TEXT              -- "hard" | "soft" | "downgrade"
  reset_at      TIMESTAMP

request_log:
  request_id    TEXT PRIMARY KEY
  team_id       TEXT
  model         TEXT
  prompt_tokens INTEGER
  completion_tokens INTEGER
  estimated_tokens  INTEGER
  latency_ms    INTEGER
  status        TEXT
  created_at    TIMESTAMP
```

### 3.8 Observability

Every request emits one JSON log line (stdout / file, structured for ingestion):

```json
{
  "timestamp": "2026-05-23T10:30:00Z",
  "request_id": "req_abc123",
  "team": "cloud-engineering",
  "model": "claude-sonnet-4-6",
  "prompt_tokens": 842,
  "completion_tokens": 341,
  "total_tokens": 1183,
  "estimated_tokens": 850,
  "latency_ms": 2340,
  "status": "success",
  "quota_remaining": 4187234,
  "routing_strategy": "static",
  "backend": "bedrock"
}
```

Metrics (Datadog DogStatsD or Prometheus):

```
llm_gateway.request.count          [team, model, status]
llm_gateway.tokens.prompt          [team, model]
llm_gateway.tokens.completion      [team, model]
llm_gateway.latency.ms             [team, model]
llm_gateway.quota.pct_used         [team]
llm_gateway.quota.remaining        [team]
llm_gateway.errors.count           [team, model, error_type]
```

---

## 4. Request Flow (Sequence)

```
Client → Gateway
  1. Auth middleware: resolve team from API key
  2. Quota middleware: check budget, apply enforcement mode
  3. Token estimator: estimate prompt tokens via tiktoken
  4. Router: select backend per routing strategy
  5. Backend adapter: send request, stream response
  6. Post-accounting: read actual tokens from response, update state store
  7. Observability: emit JSON log + metrics
  → Client receives response (streamed)
```

---

## 5. Configuration Schema

```yaml
# gateway.yaml
gateway:
  admin_key: "admin-xxxx"
  metrics_backend: "stdout"  # stdout | datadog | prometheus

teams:
  cloud-engineering:
    api_key: "ce-xxxx"
    monthly_token_budget: 5_000_000
    models_allowed:
      - claude-sonnet-4-6
      - llama-local
    rate_limit_rpm: 60
    enforcement_mode: hard       # hard | soft | downgrade
    downgrade_threshold_pct: 80  # trigger downgrade at 80% usage
    downgrade_to: llama-local
    routing_strategy: static     # static | cost_aware | fallback | shadow

backends:
  claude-sonnet-4-6:
    type: bedrock
    model_id: anthropic.claude-sonnet-4-6
    cost_per_1k_prompt: 0.003
    cost_per_1k_completion: 0.015

  llama-local:
    type: llama_cpp
    base_url: http://localhost:8080
    cost_per_1k_prompt: 0.0
    cost_per_1k_completion: 0.0
```

---

## 6. Technology Stack

| Component | Choice | ADR |
|-----------|--------|-----|
| Framework | FastAPI | [ADR-001](../adr/ADR-001-fastapi.md) |
| State store (phase 1) | SQLite | [ADR-002](../adr/ADR-002-state-store.md) |
| State store (phase 2+) | Redis | [ADR-002](../adr/ADR-002-state-store.md) |
| Token counting | tiktoken | [ADR-003](../adr/ADR-003-token-counting.md) |
| Team config | YAML | [ADR-004](../adr/ADR-004-team-config.md) |
| Observability | stdout JSON + DogStatsD | — |
| Python version | 3.11+ | — |

---

## 7. Open Questions

| Question | Resolution | Date |
|----------|------------|------|
| Streaming: how to count tokens before stream ends? | Estimate pre-request, reconcile post-stream | 2026-05-23 |
| SQLite concurrent writes under load? | Acceptable for POC; Redis upgrade path in ADR-002 | 2026-05-23 |
| Dashboard tech? | Static HTML served by gateway for POC; Grafana optionally | TBD |

---

## 8. Revision History

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 0.1 | 2026-05-23 | D. Scheiderman | Initial draft |
