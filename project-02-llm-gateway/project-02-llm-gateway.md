# Project 2 — LLM Gateway / Cost Governance
**Skill area:** LLM gateway and cost governance  
**Format:** Design + build (mix)  
**Estimated duration:** 10 days

---

## Overview

Build a lightweight Python gateway that sits in front of one or more LLM backends (Bedrock, local llama.cpp, OpenAI-compatible endpoints), enforces per-team token budgets, logs usage to Datadog, and exposes a cost dashboard. This directly operationalizes the Bifrost vs. LiteLLM evaluation you have already done — building it yourself, even crudely, will make any vendor decision far sharper.

---

## The mental model

An LLM gateway has four jobs:

1. **Routing** — direct requests to the right model backend
2. **Enforcement** — block or throttle requests that exceed quotas
3. **Observability** — emit metrics and logs for every request
4. **Abstraction** — give consumers a single endpoint regardless of what's behind it

Most teams reach for LiteLLM or a managed solution before understanding what they actually need. Building your own first — even a minimal version — teaches you exactly what those tools are solving and where they cut corners.

---

## Phase 1 — Core gateway (Days 1–3)

### Stack

| Component | Choice | Notes |
|---|---|---|
| Framework | FastAPI | Async support, easy OpenAI-compatible routing |
| Token counting | `tiktoken` | Pre-request estimation before sending |
| State store | Redis or SQLite | Redis preferred for quota enforcement |
| Config | YAML or environment variables | Team definitions, quota limits |

### Minimum viable routes

```
POST /v1/chat/completions   # OpenAI-compatible — drop-in for most clients
GET  /v1/models             # List available backends
GET  /admin/usage           # Per-team usage summary
GET  /admin/quota           # Current quota status
POST /admin/reset           # Reset quota counters (admin only)
```

### Request lifecycle

```
Client request
  → Auth middleware (API key → team identity)
  → Pre-flight quota check (would this request exceed budget?)
  → Token estimation (tiktoken before sending)
  → Route to backend (Bedrock / llama.cpp / other)
  → Response stream passthrough
  → Post-request accounting (actual tokens from response headers)
  → Metric emission (Datadog / stdout)
```

---

## Phase 2 — Quota enforcement (Days 4–5)

### Data model

```python
# Team configuration (YAML)
teams:
  cloud-engineering:
    api_key: "ce-xxxx"
    monthly_token_budget: 5_000_000
    models_allowed: ["claude-sonnet-4-20250514", "llama-local"]
    rate_limit_rpm: 60

  compliance:
    api_key: "co-xxxx"
    monthly_token_budget: 2_000_000
    models_allowed: ["claude-sonnet-4-20250514"]
    rate_limit_rpm: 20
```

### Enforcement modes

Implement all three and make them configurable per team:

- **Hard block** — reject request when quota is exhausted, return HTTP 429
- **Soft cap** — allow overage but emit a warning metric and alert
- **Downgrade** — route to a cheaper/local model when quota is near limit (most interesting to implement)

### Quota reset strategy

- Monthly reset on calendar boundary
- Carry-over option (unused budget rolls into next month, capped at 2x)
- Manual override via admin API (for incident response)

---

## Phase 3 — Observability (Days 6–7)

Every request should emit the following:

### Metrics (Datadog or Prometheus)

```
llm_gateway.request.count          tags: team, model, status
llm_gateway.tokens.prompt          tags: team, model
llm_gateway.tokens.completion      tags: team, model
llm_gateway.latency.ms             tags: team, model, percentile
llm_gateway.quota.pct_used         tags: team
llm_gateway.quota.remaining        tags: team
llm_gateway.errors.count           tags: team, model, error_type
```

### Structured logs (JSON)

```json
{
  "timestamp": "2026-05-22T10:30:00Z",
  "request_id": "req_abc123",
  "team": "cloud-engineering",
  "model": "claude-sonnet-4-20250514",
  "prompt_tokens": 842,
  "completion_tokens": 341,
  "total_tokens": 1183,
  "latency_ms": 2340,
  "status": "success",
  "quota_remaining": 4_187_234
}
```

### Cost dashboard

Build a simple dashboard (Grafana, Datadog, or even a static HTML page served by the gateway) showing:

- Monthly spend by team (tokens × cost-per-token)
- Daily trend
- Model distribution (which backends are getting traffic)
- Teams approaching quota limit (alert threshold at 80%)

---

## Phase 4 — Multi-backend routing (Days 8–9)

### Backend abstraction

Implement a common interface so adding a new backend requires only a new adapter:

```python
class LLMBackend:
    async def complete(self, messages, model, **kwargs) -> CompletionResponse:
        raise NotImplementedError

class BedrockBackend(LLMBackend): ...
class LlamaCppBackend(LLMBackend): ...
class OpenAICompatBackend(LLMBackend): ...
```

### Routing strategies to implement

- **Static** — team config maps to a specific backend
- **Cost-aware** — route to cheapest backend that can satisfy the request
- **Fallback** — primary backend, fallback on error or timeout
- **Shadow** — send to two backends, compare responses, return primary (useful for model evaluation)

The shadow routing mode is particularly valuable — it lets you run a local model alongside Claude and compare outputs without changing the client experience.

---

## Phase 5 — Comparison document (Day 10)

Write a structured comparison of your build versus Bifrost and LiteLLM. Use the experience of having built it to be specific.

### Comparison dimensions

| Dimension | Your build | Bifrost | LiteLLM |
|---|---|---|---|
| Quota enforcement | | | |
| Multi-backend routing | | | |
| Observability depth | | | |
| Operational overhead | | | |
| Enterprise auth (OIDC/SAML) | | | |
| Audit logging for compliance | | | |
| Cost to operate | | | |

This document is your primary artifact for the enterprise context — it shows you evaluated build vs. buy rigorously.

---

## Deliverables checklist

- [ ] Running gateway with at least 2 model backends wired up
- [ ] Per-team quota enforcement with all three enforcement modes
- [ ] Cost dashboard showing spend, trends, and quota status
- [ ] Structured logging and metrics emission
- [ ] Demo: what happens when a team hits their limit
- [ ] Comparison document: your build vs. Bifrost vs. LiteLLM

---

## Where to start right now

Stand up a FastAPI app with a single `/v1/chat/completions` route that proxies to one backend. Get a real request flowing end-to-end, log the token counts, and write them to a SQLite table. Everything else — quota enforcement, multi-backend, dashboards — is built on top of that one working loop.
