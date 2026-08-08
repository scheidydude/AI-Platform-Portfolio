# DESIGN-001 — Sandboxed Tool Execution Architecture (gVisor)

**Version:** 1.2
**Date:** 2026-08-07
**Author:** David Scheiderman
**Status:** Draft
**Project:** Project 07 — Sandboxed Tool Execution (gVisor)

Requirements this design satisfies are specified in [SRS-001](../srs/SRS-001.md). See [ADR-001](../adr/ADR-001-runsc-secondary-runtime.md), [ADR-002](../adr/ADR-002-additive-execution-mode.md), [ADR-003](../adr/ADR-003-host-local-no-auth-api.md), and [ADR-004](../adr/ADR-004-squid-egress-proxy.md) for the decisions behind this architecture.

**Revision note (v1.1):** Rewritten after Phase 0 recon found Orchid's real isolation surface (`ContainerRunner`, `WorkerResult`/`TaskContext`, `isolation.*` config) — see `findings.md`. v1.0 imagined a new standalone "Sandbox Execution API" service; this version hardens the existing `ContainerRunner` in place instead.

**Revision note (v1.2):** The Traefik-based allowlist assumption in §3 Phase 3 was also wrong — the host's Traefik is ingress-only. Replaced with a dedicated Squid forward-proxy sidecar (ADR-004).

---

## 1. Overview

Harden Orchid's existing container-based task isolation with gVisor (`runsc`) as the runtime, real resource ceilings, and default-deny network egress. Orchid already isolates agent task execution generically through `ContainerRunner` whenever `isolation.container_enabled` is set — today that path runs plain default-runtime Docker with no memory/CPU/network limits at all. This closes a specific portfolio gap (container-level secure execution) by hardening infrastructure that already exists, rather than building a parallel one. It is an integration and hardening project on top of gVisor's existing runtime, not a from-scratch sandbox implementation.

## 2. Architecture

```
Orchid Orchestrator (any agent — TesterAgent used for the PoC demo)
        │  isolation.container_enabled=true
        ▼
ContainerRunner.run_task_isolated()                        [existing]
        │  - builds `docker run` command from isolation.* config
        │  - --runtime={runc|runsc}                          [FR-1, FR-2, ADR-001]
        │  - --memory, --cpus                                 [FR-2]
        │  - --network none (default), or an internal-only network + proxy env
        │    vars when an egress allowlist is configured        [FR-3, ADR-004]
        ▼
gVisor (runsc) container: python:3.12-slim running orchid.worker_subprocess
        │  - resource limits enforced by Docker + gVisor sentry
        │  - syscall logging via gVisor sentry (strace-equivalent)  [FR-5]
        │
        │  (allowlisted only) HTTP_PROXY/HTTPS_PROXY ──────────────┐
        ▼                                                          ▼
WorkerResult{task_id, success, result, error, duration_s, cpu_seconds,   Squid sidecar (dual-homed:
             + optional stdout, stderr, exit_code}            [FR-4]      internal net + external net)
        ▼                                                          │  - dstdomain ACL allowlist
Existing consumers unchanged: orchestrator.py, remote/worker_server.py,   - deny all else       [ADR-004]
remote/dispatcher.py, worker_subprocess.py                          ▼
                                                                  Internet (allowlisted domains only)
```

**Host:** NucBox EVO X2, alongside the existing Docker/Traefik stack (Traefik is unrelated to this — ingress only, see ADR-004).
**Runtime:** `runsc` installed as an alternate Docker runtime, selected via a new `isolation.container_runtime` config key — default remains `runc` so existing behavior is unchanged unless explicitly opted in ([ADR-001](../adr/ADR-001-runsc-secondary-runtime.md)).
**Invocation path:** Local only, through `ContainerRunner`/`SubprocessRunner`. Not exposed through `remote/worker_server.py` (binds all interfaces; out of scope, see [ADR-003](../adr/ADR-003-host-local-no-auth-api.md)).
**Egress:** Default `--network none` (no infrastructure needed). An allowlist attaches the sandbox to a Docker `--internal` network with no outside route, reachable only by the Squid sidecar, which is itself dual-homed onto a normal external-facing network and enforces the domain allowlist via ACL ([ADR-004](../adr/ADR-004-squid-egress-proxy.md)).

## 3. Phased Implementation

| Phase | Satisfies | Description |
|---|---|---|
| 1 — Runtime Setup | FR-1 | Install/configure `runsc`; verify isolation via syscall-interception test |
| 2 — Hardened `ContainerRunner` | FR-2, FR-4 | Add `isolation.container_runtime`/`container_memory_mb`/`container_cpus` config; wire into the existing `docker run` call; extend `WorkerResult` additively |
| 3 — Network Policy | FR-3 | `--network none` by default; explicit domain allowlist via a dedicated Squid forward-proxy sidecar |
| 4 — Verification Across Isolation Paths | FR-4 | Confirm existing `WorkerResult` consumers (orchestrator, remote worker server/dispatcher, worker subprocess) are unaffected; demo via `TesterAgent` running under `isolation.container_enabled` + `runsc` |
| 5 — Observability | FR-5 | Per-execution syscall trace, associated with task ID, surfaced in ccview/PM Dashboard |
| 6 — Multi-Tenant Quotas (stretch) | FR-6 | cgroup-based per-tenant quotas, demonstrated with 2 concurrent tenants |

Full phase-by-phase acceptance criteria live in `task_plan.md`; requirement-level acceptance criteria live in [SRS-001](../srs/SRS-001.md).

## 4. Deliverables for Portfolio

- Working demo: an Orchid agent task (via `TesterAgent`) executed in a `runsc`-isolated container, with resource limits and network policy enforced, using Orchid's existing task/result plumbing unmodified
- Syscall-interception isolation proof (documented output)
- This architecture doc + a short write-up covering design decisions and trade-offs vs. the Firecracker approach ([Project 08](../../../project-08-firecracker-sandbox/))
- Short write-up: "why gVisor here, what it doesn't solve, what Firecracker adds" — this is the piece that shows systems judgment in an interview, not just implementation
- A documented example of a design assumption that didn't survive contact with the real codebase (v1.0 → v1.1 revision) — itself legitimate portfolio signal about doing recon before building

## 5. Effort Estimate

Roughly 1–2 weekends for Phases 1–4 (working, demoable). Phases 5–6 add another weekend if pursued. Hardening `ContainerRunner` in place is smaller scope than the original standalone-service plan, so this estimate is likely conservative.
