# DESIGN-002 — Build vs. Buy: LLM Gateway Vendor Comparison

**Version:** 1.0 (Final)  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Final

---

## 1. Purpose and Method

This document compares three LLM gateway implementations across seven operational dimensions:

- **This build** — the POC built in this project (Python / FastAPI / SQLite / Prometheus)
- **LiteLLM** — open-source Python proxy by BerriAI; the dominant community choice
- **Bifrost** — open-source Go proxy by MaximHQ; performance-first design

The analysis is grounded in the experience of building the equivalent from scratch. Every claim about "what it takes to implement X" is informed by having implemented it. That specificity is what separates this from a feature-checklist comparison.

---

## 2. Summary Table

| Dimension | This Build | LiteLLM | Bifrost |
|-----------|-----------|---------|---------|
| **Quota enforcement** | ✅ Hard / soft / downgrade; SQLite (race-prone) → Redis path | ✅ Full budgets per team/user/model; Redis-backed; battle-tested | ⚠️ Basic rate limiting; budget management limited |
| **Multi-backend routing** | ✅ Static / cost-aware / fallback / shadow | ✅ Static / fallback / round-robin / lowest-latency / lowest-cost / usage-based | ✅ Static / round-robin / fallback; no shadow mode |
| **Observability depth** | ✅ Prometheus + structured JSON + cost per request + SQLite history | ✅ Prometheus + 20+ callback integrations (Langfuse, Datadog, Helicone, S3, etc.) | ⚠️ Prometheus + basic access logs; limited callback ecosystem |
| **Operational overhead** | ✅ Low (single process, SQLite) → ⚠️ Medium (Redis in prod) | ⚠️ Medium–High (Python, Redis required in prod, Postgres for logging) | ✅ Low (Go binary, Redis optional, minimal deps) |
| **Enterprise auth (OIDC/SAML)** | ❌ API key + YAML only | ✅ Enterprise: SSO, OIDC, RBAC, team management UI | ⚠️ API key; some enterprise options; less mature than LiteLLM |
| **Audit logging for compliance** | ⚠️ SQLite request_log (complete, not tamper-evident) | ✅ Postgres persistence; callback integrations; Enterprise compliance features | ⚠️ Structured logs only; no durable audit store built-in |
| **Cost to operate** | ✅ Zero license; your infra only; you own the maintenance burden | ✅ Open-source free; Enterprise has licensing; Redis + Postgres infra required | ✅ Open-source; lowest infra cost (Go binary); minimal memory |

---

## 3. Dimension Deep Dives

### 3.1 Quota Enforcement

**What it actually takes to build**

Quota enforcement has two hard problems that aren't obvious until you implement them:

*The streaming accounting problem.* With streaming responses, you don't know actual token counts until the stream ends. A pre-flight check using tiktoken estimates works well enough — but the actual debit can only happen post-stream. Our implementation uses a `try/finally` block inside an async generator:

```python
async def generate():
    try:
        async for chunk in backend.stream(body):
            # parse usage from final SSE chunk
            yield chunk
    finally:
        # debit happens here, after stream ends
        await store.increment(team, month, actual_tokens)
```

If the client disconnects mid-stream, `finally` still runs — but with partial usage. We accept this as a known limitation. Production systems need reservation-based accounting: reserve estimated tokens at start, release the delta at end.

*The concurrent write problem.* With SQLite under concurrent load, two requests can both read `4,999,500 / 5,000,000` tokens, both pass the quota check, and both send — resulting in `5,001,183` total, a quota bust. WAL mode reduces this but doesn't eliminate it. The fix is Redis `INCR`, which is atomic by design. We documented this in ADR-002 and kept SQLite as the POC state store with Redis as the declared upgrade path.

**LiteLLM**: Solves both problems. Redis-backed with atomic operations. Per-team, per-model, and per-user budget dimensions. Monthly and daily reset periods. Carry-over support. Has been battle-tested across the streaming edge cases. The implementation is in `litellm/proxy/utils.py` — worth reading.

**Bifrost**: Basic rate limiting (RPM/TPM) but not the full budget governance model. No soft-cap or downgrade enforcement modes. Primarily useful for traffic shaping, not cost governance.

**Verdict**: For serious cost governance, LiteLLM's budget management is years ahead. The POC build demonstrates the same concepts but the edge cases (streaming, concurrency, carry-over) would take months to harden.

---

### 3.2 Multi-Backend Routing

**What it actually takes to build**

Routing sounds simple — map team to backend — until you implement the interesting modes.

*Cost-aware routing* is straightforward: compare `cost_per_1k_prompt + cost_per_1k_completion` across `models_allowed`, pick the minimum. O(n) per request, stateless. The limitation we discovered: cost-per-token doesn't account for quality-per-token. A $0 Ollama model that produces worse output may require more human review or retry calls, which isn't captured in the metric.

*Fallback routing* has a scope constraint we hard-coded: fallback only applies to non-streaming requests. Once streaming starts (first byte sent to client), you cannot redirect mid-stream. Any gateway claiming "streaming fallback" is either buffering the response (killing latency) or handling only the initial connection failure.

*Shadow routing* was the most architecturally interesting. The key constraints:
1. Shadow response must never affect client latency (fire-and-forget)
2. Shadow tasks must not be GC'd while running (we used a `set` + `add_done_callback`)
3. Shadow requests should NOT decrement team quota (they're operator tooling)
4. Shadow results need correlation with the primary request (`request_id`)

```python
_shadow_tasks: set[asyncio.Task] = set()

task = asyncio.create_task(_run_shadow(shadow_backend, body, request_id, ...))
_shadow_tasks.add(task)
task.add_done_callback(_shadow_tasks.discard)
```

The shadow comparison log (`event: shadow_comparison`) is the raw data for model evaluation without touching clients. This pattern is underused in the industry.

**LiteLLM**: More routing strategies than we built — lowest-latency (tracks real p50/p99 from prior requests), usage-based routing (load balancing by current load), and latency-based with cooldown after errors. The router is stateful and learns from request history. Our Router is stateless. LiteLLM also supports `num_retries` and `timeout` per deployment, giving finer control than our binary fallback.

**Bifrost**: Round-robin and fallback. No cost-aware or shadow modes. Simpler, but covers the common cases.

**Verdict**: LiteLLM's router is significantly more capable. Shadow routing (our strongest differentiator) is not a LiteLLM feature — this is genuinely a gap. If shadow routing for model comparison is a priority, you need to build it.

---

### 3.3 Observability Depth

**What it actually takes to build**

Every request needs: a unique ID, team, model, backend, prompt tokens, completion tokens, estimated tokens, latency, status, cost, and quota state. That's 12 fields minimum. We emit these as:

1. **NDJSON** to stdout (always on, no dependencies)
2. **Prometheus counters/histograms/gauges** at `/metrics`
3. **SQLite rows** in `request_log` for historical queries

The interesting decision was the `estimated_tokens` vs `actual_tokens` split. Logging both lets you track tiktoken accuracy over time. For Ollama (LLaMA tokenizer, not BPE), the estimate can be off by 15-25% — which matters for quota pre-flight accuracy. We log the discrepancy but don't yet act on it.

Cost-per-request (`cost_usd`) flows from backend config × actual tokens and lands in both the log and SQLite. The dashboard queries SQLite for daily trend aggregation using `GROUP BY date(created_at)`.

**LiteLLM**: The callback system is the standout feature. One line of config sends every request event to Langfuse (traces), Datadog (metrics), Helicone (cost tracking), S3 (raw log archival), Sentry (errors), or a custom webhook. This is years of integration work. Building even one of these integrations (e.g., Langfuse) from scratch is a week of engineering. LiteLLM has 20+. The Prometheus endpoint is also built-in.

**Bifrost**: Prometheus metrics, structured logs. No callback ecosystem. If you need Langfuse integration, you build it yourself.

**Verdict**: For observability breadth, LiteLLM wins by an order of magnitude. Our build matches on the core metrics but has none of the downstream integrations. For a team already using Datadog or Langfuse, LiteLLM's callbacks eliminate weeks of custom work.

---

### 3.4 Operational Overhead

**What it actually takes to run**

Our POC requires:
- Python 3.11+ environment
- One process (`uvicorn gateway.main:app`)
- SQLite file (zero infra, included in stdlib)
- Optional: Redis (for atomic quota in production)

Cold start: ~2 seconds (FastAPI startup, tiktoken encoding load, DB init). Memory: ~80MB resident with tiktoken model loaded.

The upgrade path to production adds:
- Redis for atomic quota counters
- A reverse proxy (nginx/caddy) for TLS
- Process supervisor (systemd/supervisor) for restarts
- Log shipping (filebeat/fluentd) to aggregate NDJSON

That's real operational overhead, but it's well-understood infrastructure — no proprietary components.

**LiteLLM**: Production deployment requires Python, Redis (hard requirement for distributed deployments), and Postgres (for request logging and team management persistence). The recommended setup is Docker Compose with three containers. The LiteLLM proxy itself has significant startup time and memory footprint (~200-400MB). Configuration complexity is high — hundreds of YAML options, some underdocumented.

**Bifrost**: A single Go binary. ~20MB memory footprint, <200ms cold start. Redis optional. If you need a gateway that can handle 10,000 RPS with sub-millisecond overhead, Bifrost's architecture is the right starting point. Our Python gateway adds 5-20ms overhead per request just from the Python interpreter and async overhead.

**Verdict**: For lowest operational overhead, Bifrost wins. Our Python build is comparable to LiteLLM in overhead. The Go vs Python performance gap matters at scale (>1000 RPS) but is irrelevant for most team-internal LLM traffic.

---

### 3.5 Enterprise Auth (OIDC/SAML)

**What it takes to build**

Our auth model: YAML file maps API keys to team identities. One middleware function, 20 lines of code. Fast, transparent, zero dependencies. The gap: no SSO, no user-level identity, no self-service key rotation, no RBAC beyond team-level.

Adding OIDC would require:
- A JWT validation library (`python-jose` or `authlib`)
- JWKS endpoint fetching and key caching
- Token claims extraction (sub, groups, email)
- Group-to-team mapping logic
- Key rotation handling

That's roughly a week of engineering plus ongoing maintenance as identity providers update their OIDC implementations.

**LiteLLM Enterprise**: Full SSO via OIDC/SAML (Okta, Azure AD, Google Workspace), RBAC with Admin/Developer/Viewer roles, team management UI, per-user budget isolation within a team. This is the feature that justifies the Enterprise license for regulated environments (financial services, healthcare, government).

**Bifrost**: API key auth. Enterprise options exist but are less mature than LiteLLM's.

**Verdict**: If your organization requires SSO for any internal tool (and most do at >50 employees), LiteLLM Enterprise is the answer. Building OIDC from scratch is not a good use of engineering time.

---

### 3.6 Audit Logging for Compliance

**What it takes to build**

Our `request_log` SQLite table captures: request ID, team, model, backend, token counts, latency, status, cost, and timestamp. This is complete enough for internal chargebacks and incident investigation. What it lacks:

- **Tamper evidence**: rows can be deleted or edited; no hash chain
- **Long-term retention**: SQLite is a local file; no built-in replication or archival
- **Prompt/response content**: we log metadata only, not the actual messages (intentionally)
- **User-level attribution**: we identify the team, not the individual user

For SOC 2 or HIPAA audit requirements, you'd need immutable log storage (CloudTrail, S3 with object lock) and a documented retention policy. Neither of our POC nor most vendor products give you this out of the box — it's an infrastructure concern.

**LiteLLM**: Postgres persistence with configurable retention. Callback integration to S3 for archival. Enterprise audit logs with more metadata. Still requires the operator to configure immutable storage for true compliance.

**Bifrost**: Structured logs to stdout, operator-configured shipping. Same compliance gap as our build.

**Verdict**: Both vendor solutions require operator work to achieve compliance-grade audit logging. Neither eliminates the problem, but LiteLLM reduces the custom work with Postgres + S3 callback.

---

### 3.7 Cost to Operate

| Component | This Build | LiteLLM (OSS) | LiteLLM Enterprise | Bifrost |
|-----------|-----------|--------------|-------------------|---------|
| Software license | Free | Free | Paid (quoted per-org) | Free |
| Compute | 1× small VM | 1–2× VM + Redis | Same + Postgres | 1× small VM |
| Maintenance burden | High (you own it) | Medium (community) | Low (vendor support) | Medium |
| Integration time | Built to your spec | 2–5 days setup | 1–2 days + sales | 2–3 days setup |

The hidden cost of this build is maintenance. Every edge case we encountered — streaming accounting, quota race conditions, shadow task GC, tiktoken divergence for Llama — is a bug that LiteLLM has already fixed and backfilled. Owning the code means owning those bug fixes forever.

The hidden cost of LiteLLM OSS is operational complexity: Redis + Postgres add two stateful services to your infrastructure, each with their own backup/recovery/monitoring requirements.

The hidden cost of Bifrost is ecosystem — fewer community examples, fewer integrations, less documentation coverage for edge cases.

---

## 4. What Building It Taught Me

The things that were harder than expected:

**1. Streaming token accounting is the core hard problem.** The `try/finally` pattern in async generators is elegant but subtle. A client disconnecting mid-stream, a backend returning no usage metadata, or a tiktoken estimate that's wildly off for a Llama model — any of these breaks the accounting loop. LiteLLM has had years of bug reports on exactly these failure modes.

**2. Quota enforcement under concurrency requires atomic operations.** SQLite WAL mode is not a substitute for Redis `INCR`. The race condition window is small but real. Any team with >10 concurrent users will hit it occasionally.

**3. The downgrade routing mode is where enforcement and routing intersect.** Enforcement logic (quota check) needs to inform routing logic (backend selection). This coupling is architecturally awkward — it means enforcement isn't a pure middleware layer. We solved it by making downgrade override the Router, which is correct but required deliberately breaking the separation of concerns.

**4. Shadow routing needs explicit GC protection.** `asyncio.create_task()` creates a task that Python can garbage collect if no references exist. The `_shadow_tasks: set` pattern is non-obvious but necessary.

**5. Cost-per-token doesn't capture total cost of ownership.** Our cost_aware router picks Ollama (cost $0) every time. But Ollama responses may require more follow-up questions, more retries, or more human review. The real cost of a model includes quality-per-dollar, which isn't in our metric.

The things that were easier than expected:

**1. OpenAI-compatible endpoint coverage is excellent.** Ollama, llama.cpp, and most hosted APIs all speak the same protocol. One backend adapter (`OpenAICompatBackend`) covered every model we needed.

**2. Prometheus integration is minimal overhead.** Six metric definitions, one `/metrics` endpoint, 60 lines of code. Grafana works immediately.

**3. FastAPI's async/streaming is clean.** `StreamingResponse` with an async generator is the right abstraction. No boilerplate.

---

## 5. Decision Matrix

| Your situation | Recommendation |
|----------------|---------------|
| POC / learning / building intuition | Build your own first (what this project is) |
| Team <20 engineers, simple quota needs | LiteLLM OSS — 2-day setup, community support |
| Team with Okta/Azure AD SSO requirement | LiteLLM Enterprise — OIDC built-in |
| Need 10k+ RPS with <1ms gateway overhead | Bifrost — Go binary, lowest footprint |
| Need shadow routing for model comparison | Build it — no vendor does this well |
| Regulated industry (HIPAA, SOC 2) | LiteLLM Enterprise + S3 archival + legal review |
| Unusual quota logic (ML-based, user-level) | Build your own — vendors won't fit |
| Langfuse / Helicone / Datadog integration | LiteLLM — callbacks eliminate weeks of work |

---

## 6. Conclusion

Building this gateway from scratch was the right choice for this learning objective. The experience revealed which problems are genuinely hard (streaming accounting, quota concurrency), which are architectural judgment calls (downgrade coupling, shadow GC), and which are just plumbing (Prometheus, auth middleware).

The main conclusion: **LiteLLM solves the same problems we solved, plus five years of edge cases we haven't encountered yet.** For any team that isn't building an LLM gateway as a core product, LiteLLM is the correct answer. The build-vs-buy decision reduces to: do you need the customization enough to pay for it indefinitely in maintenance?

The narrow cases where building wins:
- Shadow routing for continuous model evaluation (LiteLLM doesn't have this)
- Deeply custom quota logic (ML-based token estimation, per-user sub-team budgets)
- Integration with an existing auth system that vendors don't support

Bifrost's niche is performance at scale. If you're proxying >5,000 RPS and Python interpreter overhead is measurable, a Go binary is the right architecture. That's a real constraint for large enterprise deployments, not for the use cases this project targets.

---

## 7. Revision History

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 1.0 | 2026-05-23 | D. Scheiderman | Final — Phase 5 capstone |
