# ADR-003 — Sandboxed Execution Stays Local, No Auth in v1

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

Hardened, `runsc`-backed execution could, in principle, be exposed as a multi-user service with authentication and network access — Orchid already has a candidate for that shape: `orchid/remote/worker_server.py`, a FastAPI service with a `/task` endpoint that binds all interfaces (`0.0.0.0`) for distributed multi-node task execution. P07 is a portfolio demo running on a single homelab host, not a production multi-tenant offering, and reusing that server as the sandboxing entry point would silently take on its exposure characteristics.

## Decision

Sandboxed execution is invoked locally for v1, through `ContainerRunner`/`SubprocessRunner` directly (as called from `orchestrator.py`) — not through `remote/worker_server.py` or any other network-bound service. No authentication, no external network exposure, no multi-user access control. FR-6's multi-tenant quota demonstration models tenancy via cgroup-based resource quotas only — it does not add auth or wire through the remote worker server.

## Rationale

- Building real auth/multi-tenancy infrastructure is a distinct, non-trivial scope that isn't what this project is demonstrating (isolation and resource control, not access control).
- `remote/worker_server.py` already exists and already binds `0.0.0.0` for its own (distributed-execution) purpose — reusing it for sandboxed code execution would inherit that network exposure by default, which is a materially different risk posture than "runs locally on this host."
- Scoping this out explicitly prevents scope creep into a production-hardening project that would delay the demoable Phases 1–4 artifact.

## Consequences

- This design is **not** production-ready as stated; the portfolio write-up must say so explicitly rather than implying otherwise.
- If P07 is ever extended toward remote/distributed sandboxed execution via `remote/worker_server.py`, auth and network exposure become a new, separate requirement to solve first — not an incremental addition to this project's current surface.
