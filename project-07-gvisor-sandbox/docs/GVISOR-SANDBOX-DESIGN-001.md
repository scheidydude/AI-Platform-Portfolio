# GVISOR-SANDBOX-DESIGN-001

**Project:** Sandboxed Tool Execution for Orchid (gVisor)
**Portfolio Track:** AI Platform Portfolio — Agentic Systems / Security Engineering
**Target Use Case:** Proof-of-work for Staff+ Infrastructure roles requiring sandboxing, secure execution, and multi-tenant isolation experience
**Status:** Scoped, not started
**Owner:** David Scheiderman
**Implementation Agent:** Claude Code CLI

---

## 1. Purpose

Demonstrate production-grade sandboxed code/tool execution as a first-class capability inside Orchid, using gVisor (`runsc`) as the isolation boundary. This closes a specific gap in the portfolio: container-level secure execution for untrusted agent-generated code, MCP tool calls, and PR-diff verification.

This is **not** a from-scratch sandbox implementation. It is an integration and hardening project on top of gVisor's existing runtime, wired into Orchid's existing agent lifecycle.

## 2. Background / Motivation

Orchid's `TesterAgent` currently supports a `verify_syntax_only` mode but does not execute untrusted code in an isolated boundary. Agentic systems that let an LLM generate and run code, or that expose MCP tools to external services, need a real isolation layer — this is a named requirement in multiple Staff+ infra roles (sandboxed compute environments, secure execution, multi-tenant platforms).

## 3. Goals

- Execute untrusted code/commands inside a gVisor-isolated container, invoked from Orchid
- Enforce resource ceilings: wall-clock timeout, memory limit, CPU limit
- Enforce network isolation by default (zero egress unless explicitly allowlisted)
- Surface execution results (stdout/stderr/exit code) back to the calling agent in Orchid's existing task/result schema
- Capture syscall-level observability for each execution
- Demonstrate per-tenant resource quotas (stretch goal, multi-tenancy signal)

## 4. Non-Goals

- Not building a new container runtime or sandbox technology
- Not replacing Docker as the primary Orchid execution substrate — gVisor sits alongside it as an opt-in isolation mode
- Not covering GPU-passthrough or ROCm workloads inside the sandbox (out of scope for v1)

## 5. Architecture

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
**Runtime:** `runsc` installed as an alternate Docker runtime (`--runtime=runsc`), no change to existing non-sandboxed containers.

## 6. Phased Implementation

### Phase 1 — Runtime Setup (Acceptance: `runsc` container runs and is verifiably isolated)
- Install and configure `runsc` on NucBox as a secondary Docker runtime
- Verify isolation: confirm host syscalls are intercepted (e.g. attempt a known-blocked syscall, confirm gVisor sentry intercepts it)
- Acceptance criteria:
  - [ ] `docker run --runtime=runsc` executes successfully alongside default runtime containers
  - [ ] Isolation verified via at least one syscall-interception test documented with output

### Phase 2 — Execution API (Acceptance: agent can submit code, get bounded result)
- Build thin execution service: accepts `{code, language, timeout_s, memory_mb, network: bool}`, returns `{stdout, stderr, exit_code, duration_ms}`
- Enforce timeout and memory limit; kill and report on violation
- Acceptance criteria:
  - [ ] Service rejects/kills execution exceeding timeout, returns structured error
  - [ ] Service rejects/kills execution exceeding memory limit, returns structured error
  - [ ] Successful execution returns correct stdout/stderr/exit_code for a known test script

### Phase 3 — Network Policy (Acceptance: default-deny egress, explicit allowlist works)
- Default network mode: none
- Allowlist mode: route through existing Traefik/proxy config, restrict to specified domains
- Acceptance criteria:
  - [ ] Default execution has zero network access (verified via failed curl attempt inside sandbox)
  - [ ] Allowlisted execution can reach only specified domain(s), confirmed via test

### Phase 4 — Orchid Integration (Acceptance: TesterAgent can invoke sandboxed execution as a mode)
- Add sandboxed execution as a new mode on `TesterAgent` (alongside `verify_syntax_only`)
- Wire results into existing Orchid task/result schema and task metrics capture
- Acceptance criteria:
  - [ ] `TesterAgent` can be configured to run in `sandboxed_execution` mode
  - [ ] Results appear in PM Dashboard using existing task metrics display, no schema break

### Phase 5 — Observability (Acceptance: syscall trace available per execution)
- Capture gVisor sentry syscall logs per execution, associate with task ID
- Surface summary (or link to full trace) in ccview or PM Dashboard
- Acceptance criteria:
  - [ ] Each sandboxed execution has an associated syscall log retrievable by task ID
  - [ ] At least a summary view is visible in ccview or equivalent

### Phase 6 (Stretch) — Multi-Tenant Quotas
- cgroup-based per-tenant resource quotas (e.g. tag executions by "tenant," enforce aggregate limits)
- Acceptance criteria:
  - [ ] Two concurrent "tenants" can be demonstrated with independently enforced quotas

## 7. Deliverables for Portfolio

- Working demo: agent-submitted code executed in isolated container, with resource limits and network policy enforced
- Syscall-interception isolation proof (documented output)
- Architecture diagram (this doc) + README covering design decisions and trade-offs vs. Firecracker approach
- Short write-up: "why gVisor here, what it doesn't solve, what Firecracker adds" — this is the piece that shows systems judgment in an interview, not just implementation

## 8. Effort Estimate

Roughly 1–2 weekends for Phases 1–4 (working, demoable). Phase 5–6 add another weekend if pursued.

## 9. Handover Notes for Claude Code CLI

- Repo: extend Orchid repo, new module e.g. `orchid/sandbox/`
- Reuse existing Orchid task/result schema — do not introduce a parallel result format
- Keep the execution API host-local (no need for auth/multi-user exposure in v1 — this is a portfolio demo, not a production multi-user service)
- Prioritize Phases 1–4 for a demoable artifact before touching observability/stretch goals
