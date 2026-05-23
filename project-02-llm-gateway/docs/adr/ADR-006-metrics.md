# ADR-006 — Metrics Backend: Prometheus

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

The gateway must emit operational metrics (request counts, token counts, latency, quota utilization, cost) for observability. The project spec lists three candidates: Datadog, Prometheus, or stdout.

Three real constraints:
1. **No vendor account required** — Datadog requires an account and agent
2. **Standard scrape interface** — any future infra (Grafana, Alertmanager) should work without re-coding
3. **Zero-dependency fallback** — stdout JSON logging must always work even if Prometheus isn't scraped

---

## Decision

**Prometheus via `prometheus-client`. Expose `/metrics` endpoint. Stdout JSON logging remains always-on as an independent layer.**

---

## Rationale

| Factor | Prometheus | Datadog DogStatsD | Stdout only |
|--------|-----------|-------------------|-------------|
| Account required | No | Yes (Datadog account) | No |
| Local dev works | Yes (any scraper) | Requires dd-agent | Yes |
| Industry standard | Yes | Yes (enterprise) | No |
| Grafana compatible | Yes (native) | Via plugin | Via Loki |
| Push vs pull | Pull | Push (UDP) | N/A |
| Python library | `prometheus-client` | `datadog` | stdlib |
| Code complexity | Low | Low | Already done |

Prometheus pull model is simpler to reason about in a POC: no agent, no UDP port, just `/metrics`. Any Grafana instance can scrape it. If Datadog becomes the target, a Datadog agent can scrape the Prometheus endpoint via OpenMetrics — no code change needed.

Stdout JSON logging is kept as an independent layer that fires on every request regardless of metrics backend. This means:
- Zero risk: if Prometheus is never scraped, every request is still logged
- Dual-write: the same event produces both a JSON log line and increments counters

### Metric taxonomy

All metrics follow OpenTelemetry semantic conventions where applicable:

| Metric | Type | Labels |
|--------|------|--------|
| `llm_gateway_requests_total` | Counter | team, model, backend, status, enforcement_action |
| `llm_gateway_tokens_prompt_total` | Counter | team, model, backend |
| `llm_gateway_tokens_completion_total` | Counter | team, model, backend |
| `llm_gateway_request_latency_seconds` | Histogram | team, model, backend |
| `llm_gateway_request_cost_usd_total` | Counter | team, model, backend |
| `llm_gateway_quota_used_ratio` | Gauge | team |

---

## Consequences

- `prometheus-client` added as a hard dependency (~500KB, zero transitive deps)
- `/metrics` endpoint exposed unauthenticated (acceptable for POC; production would add bearer token or network-level restriction)
- `_quota_used_ratio` Gauge is updated post-request; if no requests happen, ratio stays at last-known value (correct behavior for a gauge)
- DogStatsD support left as upgrade path: implement `record()` → `statsd.increment()` translation in a new `metrics_datadog.py` module, swap via config

---

## Alternatives Not Chosen

- **Datadog DogStatsD only**: requires agent, vendor lock-in, no local scraping
- **Stdout only**: not scrapeable; no time-series; no alerting integration
- **OpenTelemetry SDK**: correct long-term choice; too much ceremony for a POC (OTLP exporter, collector, etc.)
