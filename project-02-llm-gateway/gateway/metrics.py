from __future__ import annotations
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

registry = CollectorRegistry()

_requests = Counter(
    "llm_gateway_requests_total",
    "Total completed requests",
    ["team", "model", "backend", "status", "enforcement_action"],
    registry=registry,
)
_prompt_tokens = Counter(
    "llm_gateway_tokens_prompt_total",
    "Total prompt tokens consumed",
    ["team", "model", "backend"],
    registry=registry,
)
_completion_tokens = Counter(
    "llm_gateway_tokens_completion_total",
    "Total completion tokens consumed",
    ["team", "model", "backend"],
    registry=registry,
)
_latency = Histogram(
    "llm_gateway_request_latency_seconds",
    "End-to-end request latency",
    ["team", "model", "backend"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=registry,
)
_cost = Counter(
    "llm_gateway_request_cost_usd_total",
    "Total request cost in USD",
    ["team", "model", "backend"],
    registry=registry,
)
_quota_ratio = Gauge(
    "llm_gateway_quota_used_ratio",
    "Quota used as a fraction 0–1",
    ["team"],
    registry=registry,
)


def record(
    *,
    team: str,
    model: str,
    backend: str,
    status: str,
    enforcement_action: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_seconds: float,
    cost_usd: float,
    quota_used: int,
    quota_budget: int,
) -> None:
    labels = {"team": team, "model": model, "backend": backend}
    _requests.labels(**labels, status=status, enforcement_action=enforcement_action).inc()
    _prompt_tokens.labels(**labels).inc(prompt_tokens)
    _completion_tokens.labels(**labels).inc(completion_tokens)
    _latency.labels(**labels).observe(latency_seconds)
    _cost.labels(**labels).inc(cost_usd)
    if quota_budget > 0:
        _quota_ratio.labels(team=team).set(quota_used / quota_budget)


def prometheus_output() -> tuple[bytes, str]:
    return generate_latest(registry), CONTENT_TYPE_LATEST
