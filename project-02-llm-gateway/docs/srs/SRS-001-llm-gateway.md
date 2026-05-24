# SRS-001 — LLM Gateway Software Requirements Specification

**Version:** 1.0 (Final)  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Final

---

## 1. Purpose

Define functional and non-functional requirements for a lightweight Python LLM gateway that enforces per-team token budgets, routes requests to multiple model backends, and emits structured observability data.

Primary goal: build to understand — this POC exists to make any future vendor (Bifrost, LiteLLM) decision sharper by having built the equivalent yourself.

---

## 2. Scope

In scope:
- OpenAI-compatible API endpoint (`/v1/chat/completions`)
- Per-team authentication and identity resolution
- Pre-request token budget enforcement
- Multi-backend routing (Bedrock, llama.cpp, OpenAI-compatible)
- Structured JSON logging and metric emission
- Cost dashboard (static or Grafana)
- Admin API for quota management
- Vendor comparison document

Out of scope:
- Production hardening (HA, distributed deployment)
- Enterprise SSO / OIDC / SAML
- Streaming response transformation
- Fine-tuning or batch inference endpoints

---

## 3. Stakeholders

| Role | Person | Interest |
|------|--------|----------|
| Builder / Owner | David Scheiderman | Learning + portfolio artifact |
| Future reviewer | Hiring manager / tech lead | Evidence of system design judgment |

---

## 4. Functional Requirements

### 4.1 Request Routing

| ID | Requirement | Priority |
|----|------------|---------|
| FR-01 | Gateway MUST expose `POST /v1/chat/completions` compatible with OpenAI client SDK | Must |
| FR-02 | Gateway MUST expose `GET /v1/models` returning list of configured backends | Must |
| FR-03 | Requests MUST be routed to backend specified in team config | Must |
| FR-04 | Gateway MUST support static, cost-aware, fallback, and shadow routing strategies | Should |
| FR-05 | Shadow routing MUST send to two backends and return primary response | Should |

### 4.2 Authentication & Identity

| ID | Requirement | Priority |
|----|------------|---------|
| FR-06 | Every request MUST include a valid API key in `Authorization: Bearer` header | Must |
| FR-07 | Gateway MUST resolve API key → team identity using YAML config | Must |
| FR-08 | Unknown or missing API keys MUST return HTTP 401 | Must |

### 4.3 Quota Enforcement

| ID | Requirement | Priority |
|----|------------|---------|
| FR-09 | Gateway MUST track cumulative token usage per team per calendar month | Must |
| FR-10 | Gateway MUST support hard block mode: reject requests when quota exhausted (HTTP 429) | Must |
| FR-11 | Gateway MUST support soft cap mode: allow overage, emit warning metric | Should |
| FR-12 | Gateway MUST support downgrade mode: route to cheaper backend when quota near limit | Should |
| FR-13 | Quota thresholds and enforcement mode MUST be configurable per team in YAML | Must |
| FR-14 | Monthly quota MUST reset on calendar boundary | Must |
| FR-15 | Carry-over option: unused budget rolls to next month, capped at 2× monthly budget | Could |
| FR-16 | `POST /admin/reset` MUST allow manual quota reset per team | Must |

### 4.4 Token Accounting

| ID | Requirement | Priority |
|----|------------|---------|
| FR-17 | Gateway MUST estimate prompt tokens before sending request (tiktoken) | Must |
| FR-18 | Gateway MUST reconcile actual token counts from response headers post-request | Must |
| FR-19 | Both estimated and actual counts MUST be logged | Must |

### 4.5 Observability

| ID | Requirement | Priority |
|----|------------|---------|
| FR-20 | Every request MUST emit structured JSON log with: timestamp, request_id, team, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, status, quota_remaining | Must |
| FR-21 | Gateway MUST emit metrics: request count, token counts, latency, quota pct used, quota remaining, error count | Must |
| FR-22 | Metrics MUST include tags: team, model, status | Must |
| FR-23 | Cost dashboard MUST show: monthly spend by team, daily trend, model distribution, teams at 80%+ quota | Should |

### 4.6 Admin API

| ID | Requirement | Priority |
|----|------------|---------|
| FR-24 | `GET /admin/usage` MUST return per-team usage summary | Must |
| FR-25 | `GET /admin/quota` MUST return current quota status per team | Must |
| FR-26 | Admin endpoints MUST require separate admin API key | Should |

### 4.7 Vendor Comparison

| ID | Requirement | Priority |
|----|------------|---------|
| FR-27 | MUST produce structured comparison doc: this build vs. Bifrost vs. LiteLLM across 7 dimensions | Must |

---

## 5. Non-Functional Requirements

| ID | Requirement | Target |
|----|------------|--------|
| NFR-01 | Latency overhead added by gateway | < 20ms p99 (excluding backend latency) |
| NFR-02 | Concurrent requests supported | ≥ 10 simultaneous (POC target) |
| NFR-03 | Config reload | YAML reloaded on startup; no hot reload required for POC |
| NFR-04 | Token count accuracy | Estimate within 10% of actual; log discrepancy |
| NFR-05 | Log format | Valid JSON, one object per line (NDJSON) |

---

## 6. System Constraints

- Python 3.11+
- Single-node deployment (no distributed state required for POC)
- SQLite for Phase 1; Redis upgrade path documented in [ADR-002](../adr/ADR-002-state-store.md)
- No external auth provider required for POC

---

## 7. Acceptance Criteria

All items must be true to declare this SRS satisfied:

- [x] Gateway processes end-to-end request through at least 2 backends
- [x] Team hitting quota limit receives HTTP 429 (hard block) or downgrade routing
- [x] All requests produce valid JSON log line
- [x] `/admin/usage` returns accurate per-team token counts
- [x] Cost dashboard renders spend and quota status for configured teams
- [x] Vendor comparison doc covers all 7 dimensions with specific observations from having built this

---

## 8. Revision History

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 0.1 | 2026-05-23 | D. Scheiderman | Initial draft from project spec |
| 1.0 | 2026-05-23 | D. Scheiderman | Final — all acceptance criteria verified against Phase 1–4 build |
