# ADR-008 — Multi-Backend Routing Strategies

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

With two backends (OpenAI-compatible API + local Ollama), requests need a routing policy. Different teams have different needs: some want the best model unconditionally, some want the cheapest option, some need resilience, some want to compare outputs. A single routing strategy won't satisfy all teams.

---

## Decision

**Four named strategies, configurable per team in YAML. Implemented in a stateless `Router` class. Strategy is a team attribute, not a per-request attribute.**

| Strategy | Description |
|----------|-------------|
| `static` | Always route to `default_backend` (or first in `models_allowed`). Deterministic. |
| `cost_aware` | Among `models_allowed`, pick the backend with lowest combined cost-per-1k tokens. |
| `fallback` | Try `default_backend`; on error, try `fallback_backend`. |
| `shadow` | Send real request to `default_backend`; fire-and-forget copy to `shadow_backend`; log both. |

---

## Rationale

### Why per-team strategy (not per-request)

Teams have different SLAs and cost constraints. Cloud engineering may want resilience (fallback); AI research may want comparison data (shadow); a cost-sensitive team may always want Ollama (cost_aware). Encoding strategy in team config makes it auditable and version-controlled — no per-request magic.

### Static
Default. No complexity. 100% predictable for billing and debugging. Starting point for any team.

### Cost-aware
Eliminates a common manual process: engineers constantly checking pricing pages to decide which model to use. The gateway knows backend costs from config (`cost_per_1k_prompt`, `cost_per_1k_completion`) and picks the minimum. Useful for batch or exploratory workloads where model quality matters less than cost.

**Limitation**: cost-per-token doesn't account for quality-per-token. A cheaper model that produces worse output may require more retry calls, increasing real cost. This limitation is documented but out of scope for POC.

### Fallback
Resilience without client-side retry logic. The gateway absorbs backend failures transparently. Primary fails → try secondary → client never sees the error. Useful when primary is a cloud API (can 503) and secondary is local Ollama (always available).

**Scope**: fallback applies only to the initial connection for streaming requests. If a stream starts (first byte sent), we cannot redirect mid-stream.

### Shadow
Dual-send for model evaluation. Primary response is returned to the client with normal latency. Shadow request fires as a background `asyncio.Task` (fire-and-forget). Both results are logged with the same `request_id` for correlation. The shadow never affects client latency or quota accounting for the primary.

**Why this matters**: shadow routing lets you run Ollama alongside a cloud model in production traffic without changing any client behavior. The logged comparisons are the primary artifact for Phase 5 vendor comparison.

**Shadow quota**: shadow requests do NOT decrement the team's quota. Shadow is an operator tool, not a team-visible action. This is a deliberate choice — accounting for shadow would skew team budgets.

---

## Ollama as Second Backend

Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1`. The existing `OpenAICompatBackend` handles it with no code changes:

```yaml
backends:
  ollama:
    type: openai_compat
    base_url: "http://localhost:11434"
    api_key: ""
    model_id: "llama3.2"
    cost_per_1k_prompt: 0.0
    cost_per_1k_completion: 0.0
```

Start Ollama: `ollama serve` + `ollama pull llama3.2`

This means cost_aware routing always selects Ollama (cost 0), and shadow routing sends a copy to Ollama — creating a free comparison data set.

---

## Consequences

- `Router` is stateless — one instance shared across all requests via `app.state.router`
- Shadow tasks use `asyncio.create_task()` with a set to prevent premature GC
- Fallback changes the effective backend mid-request; accounting uses the backend that actually served the response
- Cost-aware is computed per-request but is O(n) on `models_allowed` — trivial overhead
- Adding a new strategy = one new method on `Router`; no changes to call sites

---

## Alternatives Not Chosen

- **Per-request routing header** (`X-Routing-Strategy`): useful but bypasses per-team policy; security concern (clients routing to cheap backends to dodge quotas)
- **Consistent hashing** (e.g., route by user hash): useful for cache consistency; no caching layer here
- **ML-based routing** (route by prompt complexity): interesting but far beyond POC scope
