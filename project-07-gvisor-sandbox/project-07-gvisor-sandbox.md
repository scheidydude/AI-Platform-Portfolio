# Project 07 — Sandboxed Tool Execution (gVisor)

**Skill area:** Secure execution · container isolation · multi-tenant resource control
**Format:** Infrastructure integration build
**Estimated duration:** 1–2 weekends (Phases 1–4), +1 weekend for Phases 5–6
**Status:** In progress — Phase 1 (see `task_plan.md`)
**Depends on:** None (sequenced before [Project 08](../project-08-firecracker-sandbox/))

---

## Overview

Hardens Orchid's existing container-based task isolation (`ContainerRunner`) with gVisor (`runsc`) as the runtime, real resource ceilings, and default-deny network egress. This is an integration and hardening project on top of gVisor's existing runtime — not a from-scratch sandbox, and not a new service: Orchid already isolates agent task execution generically via `ContainerRunner` whenever `isolation.container_enabled` is set, but that path runs plain default-runtime Docker with no memory/CPU/network limits today.

This closes a specific portfolio gap: container-level secure execution, resource ceilings, default-deny network egress, and syscall-level observability, which are named requirements in Staff+ infrastructure roles covering sandboxed compute and multi-tenant platforms.

Full design source: [`docs/design/DESIGN-001.md`](./docs/design/DESIGN-001.md). Requirements: [`docs/srs/SRS-001.md`](./docs/srs/SRS-001.md). Full artifact index: [`INDEX.md`](./INDEX.md).

**Revision note (2026-08-07):** The original plan assumed a new standalone execution service wired into a `TesterAgent` "mode." Phase 0 recon on the real Orchid codebase found that isolation is already generic infrastructure (`ContainerRunner`/`WorkerResult`) — see `findings.md` and ADR-002 for the corrected approach reflected below.

---

## Goals

- Run isolated Orchid agent tasks inside a gVisor-isolated container via the existing `ContainerRunner` path
- Enforce resource ceilings: memory limit, CPU limit (timeout already enforced today)
- Enforce network isolation by default (zero egress unless explicitly allowlisted)
- Surface execution results via `WorkerResult`, extended additively (no parallel schema)
- Capture syscall-level observability for each execution
- Demonstrate per-tenant resource quotas (stretch goal)

## Non-Goals

- Not building a new container runtime or sandbox technology
- Not replacing Docker as Orchid's primary execution substrate — gVisor is an opt-in isolation mode
- Not building a new standalone "Sandbox Execution API" service — superseded by hardening `ContainerRunner` directly
- Not adding per-language sandbox base images — `ContainerRunner` runs one fixed image (`python:3.12-slim`)
- Not covering GPU-passthrough or ROCm workloads inside the sandbox (v1)

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 1 — Runtime Setup | in progress | Install/configure `runsc` on NucBox as a secondary Docker runtime; verify syscall interception |
| 2 — Hardened `ContainerRunner` | not started | Add `isolation.container_runtime`/`container_memory_mb`/`container_cpus` config; extend `WorkerResult` additively |
| 3 — Network Policy | not started | Default-deny egress; explicit domain allowlist via existing Traefik/proxy |
| 4 — Verification Across Isolation Paths | not started | Confirm existing `WorkerResult` consumers unaffected; demo via `TesterAgent` |
| 5 — Observability | not started | Per-execution syscall trace, associated with task ID, surfaced in ccview/PM Dashboard |
| 6 — Multi-Tenant Quotas (stretch) | not started | cgroup-based per-tenant quotas, demonstrated with 2 concurrent tenants |

See [`docs/design/DESIGN-001.md`](./docs/design/DESIGN-001.md) for full phase-by-phase acceptance criteria.

---

## Architecture

```
Orchid Orchestrator (any agent — TesterAgent used for the PoC demo)
        │  isolation.container_enabled=true
        ▼
ContainerRunner.run_task_isolated()                        [existing]
        │  - --runtime={runc|runsc}, --memory, --cpus, --network none/allowlist
        ▼
gVisor (runsc) container: python:3.12-slim running orchid.worker_subprocess
        │  - syscall logging via gVisor sentry (strace-equivalent)
        ▼
WorkerResult{task_id, success, result, error, duration_s, cpu_seconds,
             + optional stdout, stderr, exit_code}
```

**Host:** NucBox EVO X2, alongside existing Docker/Traefik stack.

---

## Deliverables for Portfolio

- Working demo: an Orchid agent task executed in a `runsc`-isolated container, with resource limits and network policy enforced, using Orchid's existing task/result plumbing unmodified
- Syscall-interception isolation proof (documented output)
- Architecture diagram + README covering design decisions and trade-offs vs. the Firecracker approach ([Project 08](../project-08-firecracker-sandbox/))
- Short write-up: "why gVisor here, what it doesn't solve, what Firecracker adds"
- A documented example of a design assumption that didn't survive contact with the real codebase — itself legitimate portfolio signal about doing recon before building

---

## Execution Environment

This project requires Linux with `runsc` installed as a Docker runtime — it does not run on the portfolio author's macOS dev machine. Implementation happens on the NucBox EVO X2 homelab host via a Claude Code CLI session run directly there (this repo is cloned onto the NucBox for that purpose).
