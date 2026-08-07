# Project 07 — Sandboxed Tool Execution (gVisor)

**Skill area:** Secure execution · container isolation · multi-tenant resource control
**Format:** Infrastructure integration build
**Estimated duration:** 1–2 weekends (Phases 1–4), +1 weekend for Phases 5–6
**Status:** Scoped, not started
**Depends on:** None (sequenced before [Project 08](../project-08-firecracker-sandbox/))

---

## Overview

Integrates gVisor (`runsc`) as an opt-in sandboxed execution mode for untrusted agent-generated code and MCP tool calls in Orchid. This is an integration and hardening project on top of gVisor's existing runtime — not a from-scratch sandbox — wired into Orchid's `TesterAgent` lifecycle alongside its existing `verify_syntax_only` mode.

This closes a specific portfolio gap: container-level secure execution, resource ceilings, default-deny network egress, and syscall-level observability, which are named requirements in Staff+ infrastructure roles covering sandboxed compute and multi-tenant platforms.

Full design source: [`docs/GVISOR-SANDBOX-DESIGN-001.md`](./docs/GVISOR-SANDBOX-DESIGN-001.md).

---

## Goals

- Execute untrusted code/commands inside a gVisor-isolated container, invoked from Orchid
- Enforce resource ceilings: wall-clock timeout, memory limit, CPU limit
- Enforce network isolation by default (zero egress unless explicitly allowlisted)
- Surface execution results (stdout/stderr/exit code) back to the calling agent in Orchid's existing task/result schema
- Capture syscall-level observability for each execution
- Demonstrate per-tenant resource quotas (stretch goal)

## Non-Goals

- Not building a new container runtime or sandbox technology
- Not replacing Docker as Orchid's primary execution substrate — gVisor is an opt-in isolation mode
- Not covering GPU-passthrough or ROCm workloads inside the sandbox (v1)

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 1 — Runtime Setup | not started | Install/configure `runsc` on NucBox as a secondary Docker runtime; verify syscall interception |
| 2 — Execution API | not started | Thin service: `{code, language, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code, duration_ms}` |
| 3 — Network Policy | not started | Default-deny egress; explicit domain allowlist via existing Traefik/proxy |
| 4 — Orchid Integration | not started | `TesterAgent` gains `sandboxed_execution` mode; results in existing task/result schema |
| 5 — Observability | not started | Per-execution syscall trace, associated with task ID, surfaced in ccview/PM Dashboard |
| 6 — Multi-Tenant Quotas (stretch) | not started | cgroup-based per-tenant quotas, demonstrated with 2 concurrent tenants |

See [`docs/GVISOR-SANDBOX-DESIGN-001.md`](./docs/GVISOR-SANDBOX-DESIGN-001.md) for full phase-by-phase acceptance criteria.

---

## Architecture

```
Orchid Agent (e.g. TesterAgent / new SandboxAgent)
        │
        ▼
Sandbox Execution API (new, thin HTTP/local service)
        │  - validates request (code/cmd, limits, network policy)
        │  - spawns container via `runsc` runtime
        ▼
gVisor (runsc) container
        │  - resource limits via cgroups
        │  - network: none by default, explicit allowlist via egress proxy
        │  - syscall logging via gVisor sentry (strace-equivalent)
        ▼
Result capture → Orchid task/result schema → PM Dashboard / ccview
```

**Host:** NucBox EVO X2, alongside existing Docker/Traefik stack.

---

## Deliverables for Portfolio

- Working demo: agent-submitted code executed in isolated container, with resource limits and network policy enforced
- Syscall-interception isolation proof (documented output)
- Architecture diagram + README covering design decisions and trade-offs vs. the Firecracker approach ([Project 08](../project-08-firecracker-sandbox/))
- Short write-up: "why gVisor here, what it doesn't solve, what Firecracker adds"

---

## Execution Environment

This project requires Linux with `runsc` installed as a Docker runtime — it does not run on the portfolio author's macOS dev machine. Implementation happens on the NucBox EVO X2 homelab host via a Claude Code CLI session run directly there (this repo is cloned onto the NucBox for that purpose).
