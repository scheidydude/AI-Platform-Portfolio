# Production Monitoring Design — AI Help Desk Observability

**Version:** 1.0  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Final (Phase 5)  
**Scope:** Design document only — no live Datadog account required (see [ADR-0005](../adr/0005-datadog-design-only.md))  
**Implements:** SRS §7 (MON-F-01 through MON-F-07)

---

## 1. Purpose

CI evals (Phases 3–4) measure quality against synthetic test cases on code changes. Production monitoring adds a continuous quality signal over real traffic. The two systems are complementary:

| | CI Evals | Production Monitoring |
|-|----------|-----------------------|
| Data source | Curated synthetic cases | Real user requests |
| Frequency | Per PR / per push | Continuous (async) |
| Latency | Minutes | Near-real-time |
| Coverage | All 30 defined behaviors | Representative sample |
| Primary purpose | Regression gate | Drift detection |

Together they answer: *Did a code change break something?* (CI) and *Is the live system degrading over time?* (monitoring).

---

## 2. Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                    PRODUCTION REQUEST PATH                    │
│                                                               │
│  User message                                                 │
│      │                                                        │
│      ▼                                                        │
│  ┌──────────┐    sampled?    ┌──────────────────┐            │
│  │   SUT    │ ─────────────▶ │  Async job queue  │           │
│  │ (Claude  │    (see §3)    │  (e.g. Celery /  │           │
│  │  Haiku)  │               │   BullMQ / SQS)  │           │
│  └────┬─────┘               └────────┬─────────┘            │
│       │                              │                        │
│       │ response to user             │ async (non-blocking)   │
│       ▼                              ▼                        │
│  User sees reply             ┌──────────────────┐            │
│                              │   Judge call      │            │
│                              │  (claude-sonnet)  │            │
│                              └────────┬─────────┘            │
│                                       │ judgment              │
│                                       ▼                        │
│                              ┌──────────────────┐            │
│                              │ metrics_emitter   │            │
│                              │  emit_judgment()  │            │
│                              └────────┬─────────┘            │
│                                       │ DogStatsD UDP         │
│                                       ▼                        │
│                              ┌──────────────────┐            │
│                              │ Datadog Agent    │            │
│                              │ localhost:8125   │            │
│                              └────────┬─────────┘            │
│                                       │                        │
│                                       ▼                        │
│                              Datadog cloud → dashboard + alerts│
└───────────────────────────────────────────────────────────────┘
```

**Key design constraint:** The judge call is async and non-blocking. The user receives their response immediately; scoring happens in the background. This prevents judge latency (~1–2s) from affecting the user-facing SUT latency.

---

## 3. Sampling Strategy

Sampling determines which production requests receive a judge score. It balances coverage against API cost.

### 3.1 Sampling Tiers

| Tier | Sample Rate | Trigger | SRS Req |
|------|-------------|---------|---------|
| Base | 5% | All requests (random) | MON-F-01 |
| Escalation | 100% | SUT set `escalate=true` | MON-F-02 |
| Fallback | 100% | SUT output failed JSON parse | MON-F-02 |
| Error | 100% | Any SUT API error | MON-F-02 |
| User-flagged | 100% | User submitted negative feedback | MON-F-03 |
| Surge | 100% | Within 24h of model/prompt deploy | MON-F-04 |

### 3.2 Sampling Decision (pseudocode)

```python
def should_sample(request_meta: dict) -> tuple[bool, str]:
    """Returns (sample, reason)."""
    if request_meta.get("surge_window_active"):
        return True, "surge"
    if request_meta.get("user_flagged"):
        return True, "user_flagged"
    if request_meta.get("escalated") or request_meta.get("parse_error"):
        return True, "escalation_or_error"
    if random.random() < 0.05:
        return True, "base_rate"
    return False, ""
```

`sampling_reason` is attached as a tag on every emitted metric, enabling cost and coverage breakdowns per tier.

### 3.3 Surge Window Activation

A surge window is activated automatically when a new model version or judge prompt version is deployed. Implementation options:
- **Feature flag:** Set `SURGE_WINDOW_ACTIVE=true` in environment; unset 24h later via deployment script.
- **Deploy event:** Write a timestamp to a config store (Redis/DynamoDB); sampling tier checks `now - deploy_time < 24h`.

---

## 4. Metric Definitions

All metrics use the prefix `helpdesk.judge.*`. Tags are consistent across all metrics.

### 4.1 Scored Dimensions

| Metric | Type | Description |
|--------|------|-------------|
| `helpdesk.judge.faithfulness` | Gauge (1–5) | Per-request faithfulness score |
| `helpdesk.judge.task_completion` | Gauge (1–5) | Per-request task completion score |
| `helpdesk.judge.tone` | Gauge (1–5) | Per-request tone score |
| `helpdesk.judge.overall` | Gauge (1–5) | Per-request overall score |
| `helpdesk.judge.compliance` | Count | Incremented per request; tag `result:pass` or `result:fail` |

### 4.2 Request Signals

| Metric | Type | Description |
|--------|------|-------------|
| `helpdesk.request.sampled` | Count | Requests that entered the judge queue |
| `helpdesk.request.judged` | Count | Requests successfully scored |
| `helpdesk.request.judge_error` | Count | Judge call failed (API error or parse error) |
| `helpdesk.request.escalated` | Count | SUT set `escalate=true` |
| `helpdesk.request.ticket_type` | Count | Tag: `type:incident|service_request|question|out_of_scope` |
| `helpdesk.judge.latency_ms` | Histogram | End-to-end judge call duration |

### 4.3 Standard Tags

Every metric carries these tags:

| Tag | Values | Purpose |
|-----|--------|---------|
| `category` | classification, faithfulness, compliance, … | Behavior category (when known) |
| `ticket_type` | incident, service_request, question, out_of_scope | SUT output classification |
| `sampling_reason` | base_rate, surge, escalation_or_error, user_flagged | Why this request was sampled |
| `model_version` | e.g. `haiku-4-5`, `sonnet-4-6` | SUT model version |
| `prompt_version` | e.g. `sut_v1`, `sut_v2` | SUT prompt version |
| `judge_prompt` | e.g. `judge_v1` | Judge prompt version |
| `env` | production, staging | Environment |

---

## 5. Alert Definitions

Alerts are defined in Datadog monitor configuration. Thresholds derive from SRS §7.

### Alert 1 — Score Drift (P1: page on-call during business hours)

**Trigger:** 7-day rolling average of `helpdesk.judge.faithfulness` OR `helpdesk.judge.task_completion` drops more than 0.3 points below the 30-day rolling average.

**Datadog monitor type:** Anomaly detection or metric threshold with `moving_average` function.

**Query (faithfulness example):**
```
avg(last_7d):avg:helpdesk.judge.faithfulness{env:production}
  < avg(last_30d):avg:helpdesk.judge.faithfulness{env:production} - 0.3
```

**Why 0.3?** A 0.3-point drop on a 1–5 scale represents a 6% quality degradation — large enough to indicate a systematic issue, small enough to catch early regressions.

**Notification:** Slack `#ai-oncall` + PagerDuty P1.

### Alert 2 — Compliance Failure (P0: immediate page)

**Trigger:** Any `helpdesk.judge.compliance{result:fail}` event within a 24-hour rolling window.

**Datadog monitor type:** Event alert on count threshold.

**Query:**
```
sum(last_24h):sum:helpdesk.judge.compliance{result:fail,env:production}.as_count() > 0
```

**Why P0?** Any PII leak in production is a compliance incident, not a quality degradation. Requires immediate response regardless of time of day.

**Notification:** PagerDuty P0 + Slack `#ai-oncall` + `#security-incidents`.

### Alert 3 — P0 Pass Rate Degradation (P1)

**Trigger:** 7-day rolling P0 pass rate drops below 90%.

P0 pass rate = `helpdesk.request.judged{pass:true,priority:p0}` / `helpdesk.request.judged{priority:p0}`.

**Notification:** Slack `#ai-oncall` + PagerDuty P1.

### Alert 4 — Judge Error Rate (P2: notify, no page)

**Trigger:** `helpdesk.request.judge_error` rate exceeds 5% of `helpdesk.request.sampled` over a 1-hour window.

Indicates judge API issues, not SUT quality. Monitoring infra failure, not a SUT regression.

**Notification:** Slack `#ai-platform-alerts` only.

---

## 6. Dashboard Panel Specifications

Dashboard name: **AI Help Desk — Production Quality**

### Panel 1 — Overall Score (7-day rolling)

| Field | Value |
|-------|-------|
| Type | Timeseries |
| Metric | `avg:helpdesk.judge.overall{env:production}` |
| Window | 7-day rolling average |
| Y-axis | 1–5 |
| Threshold lines | Red at 3.8 (blocking gate), yellow at 4.0 |
| Purpose | Primary health indicator; first panel visible |

### Panel 2 — P0 Pass Rate

| Field | Value |
|-------|-------|
| Type | Query Value (stat) |
| Metric | `helpdesk.request.judged{pass:true,priority:p0}` / `helpdesk.request.judged{priority:p0}` |
| Window | Last 7 days |
| Conditional format | Green ≥ 100%, Yellow 90–99%, Red < 90% |
| Purpose | At-a-glance safety signal |

### Panel 3 — Compliance Fail Rate

| Field | Value |
|-------|-------|
| Type | Query Value (stat) |
| Metric | `sum:helpdesk.judge.compliance{result:fail}` (count, last 24h) |
| Window | Last 24 hours |
| Conditional format | Green = 0, Red ≥ 1 |
| Purpose | PII compliance sentinel; any non-zero is an incident |

### Panel 4 — Score Distribution

| Field | Value |
|-------|-------|
| Type | Heatmap or Distribution |
| Metrics | `helpdesk.judge.faithfulness`, `helpdesk.judge.task_completion`, `helpdesk.judge.tone`, `helpdesk.judge.overall` |
| Grouped by | Dimension (4 series) |
| Window | Last 7 days |
| Purpose | Spot which dimension is dragging overall score down |

### Panel 5 — Regressions per Deploy

| Field | Value |
|-------|-------|
| Type | Timeseries with event overlay |
| Metric | `sum:helpdesk.request.judged{pass:false}.as_count()` |
| Event overlay | Deployment events (tagged `service:ai-helpdesk`) |
| Purpose | Correlate failure spikes with deployments |

### Panel 6 — Sample Volume by Reason

| Field | Value |
|-------|-------|
| Type | Stacked bar chart |
| Metric | `sum:helpdesk.request.sampled{*} by {sampling_reason}` |
| Window | Last 7 days |
| Purpose | Ensure base-rate sample is healthy; detect surge window lingering |

### Panel 7 — Ticket Type Distribution

| Field | Value |
|-------|-------|
| Type | Pie chart |
| Metric | `sum:helpdesk.request.ticket_type{*} by {type}` |
| Window | Last 7 days |
| Purpose | Detect distribution shift (e.g. sudden spike in out_of_scope) |

### Panel 8 — Escalation Rate

| Field | Value |
|-------|-------|
| Type | Timeseries |
| Metric | `sum:helpdesk.request.escalated.as_count()` / `sum:helpdesk.request.judged.as_count()` |
| Window | 1-hour rolling |
| Threshold line | Yellow at 10% |
| Purpose | High escalation rate signals SUT confidence problems |

---

## 7. Drift Detection Logic

Drift detection distinguishes systematic degradation from random noise.

### 7.1 Mechanism

For each continuous score metric (`faithfulness`, `task_completion`, `tone`, `overall`):

1. **Baseline window:** 30-day rolling average (recalculates daily)
2. **Observation window:** 7-day rolling average
3. **Drift condition:** `baseline_avg - observation_avg > 0.3`
4. **Alert:** fire when condition holds for 2 consecutive evaluation periods (reduces false positives from brief spikes)

### 7.2 Post-Deploy Surge Analysis

When a surge window activates (100% sampling for 24h post-deploy):

1. Compute per-dimension averages from the surge window
2. Compare against the pre-deploy 7-day average
3. If any dimension drops >0.3 → trigger immediate alert (do not wait for 7-day window)
4. Log surge analysis to `eval/runs/surge_<deploy_id>.json` for audit

This provides fast regression detection after deploys without waiting for the 7-day baseline to accumulate.

### 7.3 Ticket-Type Shift Detection

Beyond score drift, a sudden shift in ticket-type distribution can indicate prompt regression. For example, if 30% of requests suddenly classify as `out_of_scope` (up from 8%), the classification behavior has changed.

Detection: Chi-squared test on 7-day vs 30-day ticket-type distribution. Alert if p < 0.01.

This is a Datadog anomaly monitor on `helpdesk.request.ticket_type` by `type` tag.

---

## 8. Metrics Emitter Integration

`src/metrics_emitter.py` demonstrates the integration pattern (see ADR-0005). It emits metrics in DogStatsD format:

- **Default:** stdout (no external dependency; usable in dev/CI)
- **Production:** UDP to `DOGSTATSD_HOST:DOGSTATSD_PORT` (defaults `localhost:8125`)

Call signature after judging a production request:

```python
from metrics_emitter import emit_judgment

emit_judgment(
    judgment={"scores": {"faithfulness": 4, ...}, "pass": True, "flags": []},
    request_meta={
        "ticket_type": "incident",
        "sampling_reason": "base_rate",
        "model_version": "haiku-4-5",
        "prompt_version": "sut_v1",
        "judge_prompt": "judge_v1",
        "env": "production",
    },
)
```

This emits all metrics from §4 with the appropriate tags.

---

## 9. Deployment Checklist

Steps to enable production monitoring on a new environment:

- [ ] Set `DOGSTATSD_HOST` and `DOGSTATSD_PORT` environment variables (or leave unset for stdout mode)
- [ ] Set `ANTHROPIC_API_KEY` for judge calls
- [ ] Configure async worker (Celery/BullMQ/SQS) to process the judge queue
- [ ] Deploy Datadog Agent on the host with DogStatsD enabled
- [ ] Import dashboard JSON (once available) into Datadog account
- [ ] Create monitors from alert definitions in §5
- [ ] Activate surge window on first deploy: set `SURGE_WINDOW_ACTIVE=true` for 24h
- [ ] Verify `helpdesk.request.sampled` appears in Datadog within 10 minutes of first traffic

---

## 10. Relationship to CI Eval

| Aspect | CI Eval | Production Monitoring |
|--------|---------|----------------------|
| Cases | 30 synthetic | Real traffic (5% + triggers) |
| Judge prompt | `judge_v1.md` (same) | `judge_v1.md` (same) |
| Gate enforcement | Hard gate on merge | Alert + on-call |
| Run artifact | `eval/runs/<id>.json` | Datadog metrics + surge JSON |
| Baseline | Last main-branch run | 30-day rolling average |
| Latency | ~2 min/run | ~1–2s per sampled request |

The same judge prompt and scoring rubric are used in both systems. A score of 4/5 on `faithfulness` means the same thing in CI as in production — this is intentional. It ensures that CI gate thresholds translate directly to production alert thresholds.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-05-23 | Initial design — Phase 5 |
