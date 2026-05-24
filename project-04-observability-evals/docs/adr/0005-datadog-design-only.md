# ADR-0005 — Production Monitoring Dashboard (Design-Only Scope)

**Date:** 2026-05-23  
**Status:** Accepted  
**Author:** David Scheiderman

---

## Context

Phase 5 requires a production monitoring dashboard. A decision must be made on implementation depth: design document only, or a working live Datadog dashboard.

## Decision

**Deliver a design document only — no live Datadog account or dashboard required.**

Phase 5 deliverable = `docs/design/monitoring-design.md` with:
- Full dashboard panel specifications (metric names, chart types, alert thresholds)
- Sampling strategy design
- Drift detection logic
- Architecture diagram showing where metrics are emitted

Optionally: emit metrics to stdout in a Datadog-compatible format (StatsD/DogStatsD) to demonstrate the integration pattern without requiring a live account.

## Consequences

**Positive:**
- No external account dependency; PoC is fully self-contained
- Design document is equally valuable for portfolio — reviewers evaluate thinking, not account access
- Reduces scope; keeps Phase 5 to 2 days as planned

**Negative:**
- Cannot demonstrate a live dashboard; must be explicit in portfolio that this is a design artifact

**Neutral:**
- If Datadog access becomes available later, `monitoring-design.md` serves as the implementation spec

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| Live Datadog (free trial) | Free trial requires credit card; adds external dependency; not necessary for portfolio |
| Prometheus + Grafana local | Different tool stack than specified; adds significant setup complexity |
