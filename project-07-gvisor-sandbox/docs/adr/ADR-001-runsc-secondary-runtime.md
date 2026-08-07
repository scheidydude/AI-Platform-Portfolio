# ADR-001 — `runsc` as a Secondary Docker Runtime

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

The NucBox EVO X2 host already runs a Docker/Traefik stack serving other, unrelated services. P07 needs to introduce gVisor-isolated execution without disrupting that existing stack.

## Decision

Install `runsc` as a secondary Docker runtime (`--runtime=runsc`), invoked explicitly per-container. The existing default-runtime containers are untouched and continue using `runc`.

## Alternatives Considered

- **Migrate the host's default runtime to `runsc`.** Rejected — would silently change isolation characteristics (and likely break compatibility or add overhead) for every existing container on the host, none of which need it.
- **Run gVisor on a separate host/VM.** Rejected for v1 — adds infrastructure the portfolio scope doesn't need; NucBox already has spare capacity and Docker's multi-runtime support makes this unnecessary.

## Consequences

- Sandboxed execution is opt-in per container; callers must explicitly request `--runtime=runsc`.
- `ContainerRunner`'s new `isolation.container_runtime` config key (FR-2) is responsible for making that runtime selection, defaulting to `runc` (unchanged behavior) — `runsc` is never a host-wide default.
- Verifying isolation (FR-1) requires a test that specifically targets `runsc`-launched containers, not just "containers on this host."
