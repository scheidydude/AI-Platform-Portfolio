# DESIGN-001 — Sandboxed Tool Execution Architecture (gVisor)

**Version:** 1.0
**Date:** 2026-08-07
**Author:** David Scheiderman
**Status:** Draft
**Project:** Project 07 — Sandboxed Tool Execution (gVisor)

Requirements this design satisfies are specified in [SRS-001](../srs/SRS-001.md). See [ADR-001](../adr/ADR-001-runsc-secondary-runtime.md), [ADR-002](../adr/ADR-002-additive-execution-mode.md), and [ADR-003](../adr/ADR-003-host-local-no-auth-api.md) for the decisions behind this architecture.

---

## 1. Overview

Demonstrate production-grade sandboxed code/tool execution as a first-class capability inside Orchid, using gVisor (`runsc`) as the isolation boundary. This closes a specific portfolio gap: container-level secure execution for untrusted agent-generated code, MCP tool calls, and PR-diff verification. It is an integration and hardening project on top of gVisor's existing runtime, not a from-scratch sandbox implementation.

## 2. Architecture

```
Orchid Agent (e.g. TesterAgent / new SandboxAgent)
        │
        ▼
Sandbox Execution API (new, thin HTTP/local service)     [FR-2]
        │  - validates request (code/cmd, limits, network policy)
        │  - spawns container via `runsc` runtime          [ADR-001]
        ▼
gVisor (runsc) container
        │  - resource limits via cgroups                   [FR-2]
        │  - network: none by default, explicit allowlist via egress proxy  [FR-3]
        │  - syscall logging via gVisor sentry (strace-equivalent)  [FR-5]
        ▼
Result capture → Orchid task/result schema → PM Dashboard / ccview  [FR-4, ADR-002]
```

**Host:** NucBox EVO X2, alongside the existing Docker/Traefik stack.
**Runtime:** `runsc` installed as an alternate Docker runtime (`--runtime=runsc`), no change to existing non-sandboxed containers ([ADR-001](../adr/ADR-001-runsc-secondary-runtime.md)).

## 3. Phased Implementation

| Phase | Satisfies | Description |
|---|---|---|
| 1 — Runtime Setup | FR-1 | Install/configure `runsc`; verify isolation via syscall-interception test |
| 2 — Execution API | FR-2 | Thin service: `{code, language, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code, duration_ms}` |
| 3 — Network Policy | FR-3 | Default-deny egress; explicit domain allowlist via existing Traefik/proxy |
| 4 — Orchid Integration | FR-4 | `TesterAgent` gains `sandboxed_execution` mode; results in existing task/result schema |
| 5 — Observability | FR-5 | Per-execution syscall trace, associated with task ID, surfaced in ccview/PM Dashboard |
| 6 — Multi-Tenant Quotas (stretch) | FR-6 | cgroup-based per-tenant quotas, demonstrated with 2 concurrent tenants |

Full phase-by-phase acceptance criteria live in `task_plan.md`; requirement-level acceptance criteria live in [SRS-001](../srs/SRS-001.md).

## 4. Deliverables for Portfolio

- Working demo: agent-submitted code executed in an isolated container, with resource limits and network policy enforced
- Syscall-interception isolation proof (documented output)
- This architecture doc + a short write-up covering design decisions and trade-offs vs. the Firecracker approach ([Project 08](../../../project-08-firecracker-sandbox/))
- Short write-up: "why gVisor here, what it doesn't solve, what Firecracker adds" — this is the piece that shows systems judgment in an interview, not just implementation

## 5. Effort Estimate

Roughly 1–2 weekends for Phases 1–4 (working, demoable). Phases 5–6 add another weekend if pursued.
