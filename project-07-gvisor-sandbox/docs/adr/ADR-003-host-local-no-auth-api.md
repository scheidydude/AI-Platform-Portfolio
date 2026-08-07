# ADR-003 — Execution API Is Host-Local, No Auth in v1

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

The execution API introduced in FR-2 could, in principle, be exposed as a multi-user service with authentication, quotas, and network exposure. P07 is a portfolio demo running on a single homelab host, not a production multi-tenant offering.

## Decision

The execution API is host-local for v1: no authentication, no external network exposure, no multi-user access control. FR-6's multi-tenant quota demonstration models tenancy via cgroup-based resource quotas only — it does not add auth.

## Rationale

- Building real auth/multi-tenancy infrastructure is a distinct, non-trivial scope that isn't what this project is demonstrating (isolation and resource control, not access control).
- Scoping this out explicitly prevents scope creep into a production-hardening project that would delay the demoable Phases 1–4 artifact.

## Consequences

- This design is **not** production-ready as stated; the portfolio write-up must say so explicitly rather than implying otherwise.
- If P07 is ever extended toward a real multi-user service, auth and network exposure become a new, separate requirement — not an incremental addition to this API's current surface.
