# Project 07 — Sandboxed Tool Execution (gVisor): Document Index

**Project:** Opt-in gVisor (`runsc`) sandboxed execution mode for Orchid's `TesterAgent`
**Goal:** Portfolio-grade artifact demonstrating secure execution, resource ceilings, and syscall observability
**Timeline:** 1–2 weekends (Phases 1–4), +1 weekend for Phases 5–6
**Status:** Scoped, not started

---

## Planning Artifacts

| Document | Purpose | Status |
|----------|---------|--------|
| [task_plan.md](task_plan.md) | Phase tracker, decisions, error log | Active |
| [findings.md](findings.md) | Research, discoveries, technical decisions | Active |
| [progress.md](progress.md) | Session log, test results, reboot check | Active |
| [HANDOFF.md](HANDOFF.md) | Entry point for the next work session | Active |

---

## Requirements

| Document | Description | Status |
|----------|-------------|--------|
| [SRS-001](docs/srs/SRS-001.md) | Software Requirements Specification — Sandboxed Tool Execution | **Draft** |

---

## Design Documents

| Document | Description | Status |
|----------|-------------|--------|
| [DESIGN-001](docs/design/DESIGN-001.md) | Sandbox execution architecture, phased implementation | **Draft** |

---

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-runsc-secondary-runtime.md) | `runsc` as a secondary Docker runtime, not a host-wide replacement | Accepted |
| [ADR-002](docs/adr/ADR-002-additive-execution-mode.md) | `sandboxed_execution` is additive to `verify_syntax_only`; reuse Orchid's task/result schema | Accepted |
| [ADR-003](docs/adr/ADR-003-host-local-no-auth-api.md) | Execution API is host-local, no auth/multi-user exposure in v1 | Accepted |

---

## Implementation (PoC)

| Artifact | Description | Status |
|----------|--------------|--------|
| Sandbox execution API (`orchid/sandbox/`) | Bounded execution service — FR-2 | Not started |
| `TesterAgent` `sandboxed_execution` mode | Orchid integration — FR-4 | Not started |
| Syscall-interception isolation proof | Documented test output — FR-1 | Not started |
| Network policy tests | Default-deny + allowlist verification — FR-3 | Not started |
| Syscall observability capture | Per-task syscall log — FR-5 | Not started |

---

## Final Rollup Checklist

- [ ] SRS complete with acceptance criteria (SRS-001: FR-1 through FR-6)
- [ ] DESIGN-001 architecture and phase table match SRS requirement IDs
- [ ] All ADRs written and accepted (ADR-001 through ADR-003)
- [ ] Phase 1 — `runsc` runs alongside default-runtime containers; isolation verified via syscall-interception test
- [ ] Phase 2 — Execution API enforces timeout and memory limits; correct results for a known test script
- [ ] Phase 3 — Default-deny egress verified; allowlist mode verified
- [ ] Phase 4 — `TesterAgent` `sandboxed_execution` mode wired into existing task/result schema, no schema break
- [ ] Phase 5 — Per-execution syscall log retrievable by task ID
- [ ] Phase 6 (stretch) — Two concurrent tenants with independently enforced quotas
- [ ] Comparison write-up vs. Firecracker (P08) drafted
- [ ] INDEX.md links all artifacts

---

*Last updated: 2026-08-07 — Scoped and scaffolded, documentation brought in line with portfolio standard. No implementation started.*
