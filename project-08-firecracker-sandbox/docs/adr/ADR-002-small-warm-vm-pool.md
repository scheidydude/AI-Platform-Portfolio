# ADR-002 — Small Warm VM Pool (2–3 VMs) for the Demo

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

FR-3 requires a pre-warmed VM pool to avoid cold-start latency on demand. Pool sizing could be tuned for realistic production load or kept minimal for demonstration purposes.

## Decision

The VM pool is capped at 2–3 warm VMs for the demo. This is a portfolio proof, not a load test.

## Rationale

- The NucBox is a single homelab host with finite memory/CPU headroom shared with other services (ROCm workloads, existing Docker/Traefik stack); a large pool competes with those.
- The interview-relevant claim is "pooling eliminates cold-start latency," which a 2–3 VM pool demonstrates as clearly as a 20-VM pool would, without the added complexity of production-grade autoscaling logic.

## Consequences

- Pool-latency numbers reported in the final comparison doc reflect small-N pool behavior only; they must not be presented as production sizing guidance.
- Autoscaling, backpressure under pool exhaustion, and multi-host pool distribution are explicitly out of scope — if pool exhaustion behavior is demonstrated at all, it's to show what happens (queue or reject), not to solve it at scale.
