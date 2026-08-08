# Project 07 — Sandboxed Tool Execution (gVisor): Document Index

**Project:** Harden Orchid's existing `ContainerRunner` isolation path with gVisor (`runsc`)
**Goal:** Portfolio-grade artifact demonstrating secure execution, resource ceilings, and syscall observability
**Timeline:** 1–2 weekends (Phases 1–4), +1 weekend for Phases 5–6
**Status:** In progress — Phases 1–4 complete; starting Phase 5

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
| [ADR-004](docs/adr/ADR-004-squid-egress-proxy.md) | Squid forward-proxy sidecar for the egress allowlist, not Traefik (host's Traefik is ingress-only) | Accepted |

---

## Implementation (PoC)

| Artifact | Description | Status |
|----------|--------------|--------|
| `runsc` installed on NucBox | Secondary Docker runtime, `release-20260803.0` | **Complete** |
| Syscall-interception isolation proof (`scripts/probe_io_uring.py`, `scripts/verify_isolation.sh`) | Kernel-identity divergence + `io_uring_setup` ENOSYS proof — FR-1 | **Complete** |
| Hardened `ContainerRunner` (`orchid/container_runner.py`) | `isolation.container_runtime`/`container_memory_mb`/`container_cpus` config, `--runtime`/`--memory`/`--cpus` flags — FR-2 | **Complete** (Orchid repo, branch `p07-gvisor-hardening`, `0eaac75`) |
| Additive `WorkerResult` fields (`orchid/worker_protocol.py`) | Optional `stdout`/`stderr`/`exit_code` — FR-4 | **Complete** |
| Squid egress-allowlist sidecar (`orchid/sandbox_egress.py`) | Default-deny (`--network none`) + `dstdomain`-ACL allowlist — FR-3, ADR-004 | **Complete** (Orchid repo, branch `p07-gvisor-hardening`, `f7e0dbf`) |
| `ContainerRunner` made actually functional (mounts, `container_env`) | Fixed 3 pre-existing bugs that meant it never worked for any task — FR-4 | **Complete** (Orchid repo, branch `p07-gvisor-hardening`, `9beaea5`) |
| Live end-to-end `TesterAgent` demo | Real LLM call + pytest run under `runsc` + memory cap + egress allowlist — FR-4 | **Complete** |
| Syscall observability capture | Per-task syscall log — FR-5 | Not started |

---

## Final Rollup Checklist

- [ ] SRS complete with acceptance criteria (SRS-001: FR-1 through FR-6)
- [ ] DESIGN-001 architecture and phase table match SRS requirement IDs
- [x] All ADRs written and accepted (ADR-001 through ADR-004) — ADR-002 revised after Phase 0 recon; ADR-004 added when the Traefik-egress assumption also proved wrong
- [x] Phase 1 — `runsc` runs alongside default-runtime containers; isolation verified via syscall-interception test (kernel-identity divergence + `io_uring_setup` ENOSYS)
- [x] Phase 2 — Hardened `ContainerRunner` enforces memory/CPU limits under `runsc`; `WorkerResult` extended additively (memory-OOM proof: `exit 137` at 64m cap vs. clean completion unconstrained)
- [x] Phase 3 — Default-deny egress verified (DNS resolution fails under `--network none`); allowlist verified live over HTTP and HTTPS, under both `runc` and `runsc`, including a non-allowlisted-domain 403 rejection
- [x] Phase 4 — Existing `WorkerResult` consumers unaffected (verified per-file, zero regressions); real live `TesterAgent` demo succeeded end-to-end under the fully hardened path (found and fixed 3 pre-existing bugs that had made `ContainerRunner` non-functional for any task before this)
- [ ] Phase 5 — Per-execution syscall log retrievable by task ID
- [ ] Phase 6 (stretch) — Two concurrent tenants with independently enforced quotas
- [ ] Comparison write-up vs. Firecracker (P08) drafted
- [ ] INDEX.md links all artifacts

---

*Last updated: 2026-08-07 — Phases 1–4 complete. `runsc` installed and syscall-interception isolation verified; `ContainerRunner` hardened with runtime/memory/CPU config; egress default-deny + Squid allowlist sidecar built and live-verified (including a real gVisor DNS-resolution limitation found and fixed along the way); a real, live end-to-end `TesterAgent` demo succeeded under the fully hardened path, after finding and fixing 3 pre-existing bugs that meant `isolation.container_enabled` had never worked for any task before this project touched it. All committed to the Orchid repo's `p07-gvisor-hardening` branch (`0eaac75`, `f7e0dbf`, `9beaea5`; not merged to `main`). Also surfaced and cleaned up a pre-existing, unrelated MCP-subprocess leak in Orchid's test suite while attempting a full-suite regression check — see `findings.md`.*
