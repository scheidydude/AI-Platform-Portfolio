# Project 07 — Sandboxed Tool Execution (gVisor): Document Index

**Project:** Harden Orchid's existing `ContainerRunner` isolation path with gVisor (`runsc`)
**Goal:** Portfolio-grade artifact demonstrating secure execution, resource ceilings, and syscall observability
**Timeline:** 1–2 weekends (Phases 1–4), +1 weekend for Phases 5–6
**Status:** In progress — Phase 1 complete; starting Phase 2

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
| [SRS-001](docs/srs/SRS-001.md) | Software Requirements Specification — Sandboxed Tool Execution (v1.1, revised after Phase 0 recon) | **Draft** |

---

## Design Documents

| Document | Description | Status |
|----------|-------------|--------|
| [DESIGN-001](docs/design/DESIGN-001.md) | Hardened `ContainerRunner` architecture, phased implementation (v1.1) | **Draft** |

---

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-runsc-secondary-runtime.md) | `runsc` as a secondary Docker runtime, not a host-wide replacement | Accepted |
| [ADR-002](docs/adr/ADR-002-additive-execution-mode.md) | Harden `ContainerRunner` + extend `WorkerResult` additively, not a new standalone execution service | Accepted (revised) |
| [ADR-003](docs/adr/ADR-003-host-local-no-auth-api.md) | Sandboxed execution stays local via `ContainerRunner`, not exposed via `remote/worker_server.py`; no auth in v1 | Accepted |

---

## Implementation (PoC)

| Artifact | Description | Status |
|----------|--------------|--------|
| `runsc` installed on NucBox | Secondary Docker runtime, `release-20260803.0` | **Complete** |
| Syscall-interception isolation proof (`scripts/probe_io_uring.py`, `scripts/verify_isolation.sh`) | Kernel-identity divergence + `io_uring_setup` ENOSYS proof — FR-1 | **Complete** |
| Hardened `ContainerRunner` (`orchid/container_runner.py`) | `isolation.container_runtime`/`container_memory_mb`/`container_cpus` config, `--runtime`/`--memory`/`--cpus` flags — FR-2 | Not started |
| Additive `WorkerResult` fields (`orchid/worker_protocol.py`) | Optional `stdout`/`stderr`/`exit_code` — FR-4 | Not started |
| Network policy tests | Default-deny + allowlist verification — FR-3 | Not started |
| Syscall observability capture | Per-task syscall log — FR-5 | Not started |

---

## Final Rollup Checklist

- [ ] SRS complete with acceptance criteria (SRS-001: FR-1 through FR-6)
- [ ] DESIGN-001 architecture and phase table match SRS requirement IDs
- [x] All ADRs written and accepted (ADR-001 through ADR-003) — ADR-002 revised after Phase 0 recon
- [x] Phase 1 — `runsc` runs alongside default-runtime containers; isolation verified via syscall-interception test (kernel-identity divergence + `io_uring_setup` ENOSYS)
- [ ] Phase 2 — Hardened `ContainerRunner` enforces memory/CPU limits under `runsc`; `WorkerResult` extended additively
- [ ] Phase 3 — Default-deny egress verified; allowlist mode verified
- [ ] Phase 4 — Existing `WorkerResult` consumers unaffected; `TesterAgent` demo runs correctly under the hardened path
- [ ] Phase 5 — Per-execution syscall log retrievable by task ID
- [ ] Phase 6 (stretch) — Two concurrent tenants with independently enforced quotas
- [ ] Comparison write-up vs. Firecracker (P08) drafted
- [ ] INDEX.md links all artifacts

---

*Last updated: 2026-08-07 — Phase 0 recon complete (Traefik confirmation pending); SRS-001/DESIGN-001/ADR-002 revised after discovering the real `ContainerRunner`/`WorkerResult` integration surface. Phase 1 complete: `runsc` installed and syscall-interception isolation verified (see `findings.md`).*
