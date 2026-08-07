# Project 08 — MicroVM Execution Backend with Checkpoint/Restore (Firecracker): Document Index

**Project:** Firecracker-backed microVM execution layer with snapshot/restore, alternative backend to [Project 07](../project-07-gvisor-sandbox/)
**Goal:** Portfolio-grade artifact demonstrating durable execution across simulated host failure
**Timeline:** 2–3 weekends (Phases 1–5), +1 weekend for Phase 6
**Status:** Scoped, not started — blocked on P07 reaching a finalized execution API contract (P07 Phase 2)

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
| [SRS-001](docs/srs/SRS-001.md) | Software Requirements Specification — MicroVM Execution Backend | **Draft** |

---

## Design Documents

| Document | Description | Status |
|----------|-------------|--------|
| [DESIGN-001](docs/design/DESIGN-001.md) | MicroVM execution architecture, phased implementation | **Draft** |

---

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-reuse-p07-execution-contract.md) | Reuse P07's execution API contract verbatim, no new contract design | Accepted |
| [ADR-002](docs/adr/ADR-002-small-warm-vm-pool.md) | Cap warm VM pool at 2–3 VMs for the demo | Accepted |
| [ADR-003](docs/adr/ADR-003-honest-cold-start-reporting.md) | Report real cold-start numbers on AMD/ROCm hardware, no target chasing | Accepted |

---

## Implementation (PoC)

| Artifact | Description | Status |
|----------|--------------|--------|
| Stripped kernel + Alpine rootfs image | Minimal bootable microVM — FR-1 | Not started |
| Execution API (Firecracker backend) | Contract parity with P07 — FR-2 | Not started |
| VM Pool Manager | 2–3 warm VMs, async replenish — FR-3 | Not started |
| Snapshot mechanism | Mid-execution snapshot to disk — FR-4 | Not started |
| Restore mechanism | Snapshot → new process, task resumption — FR-5 | Not started |
| Orchid FSM checkpoint/restore wiring | Lifecycle integration — FR-6 | Not started |

---

## Final Rollup Checklist

- [ ] SRS complete with acceptance criteria (SRS-001: FR-1 through FR-6)
- [ ] DESIGN-001 architecture and phase table match SRS requirement IDs
- [ ] All ADRs written and accepted (ADR-001 through ADR-003)
- [ ] Phase 1 — MicroVM boots and runs a task; cold start measured and documented
- [ ] Phase 2 — Execution API contract parity with P07 verified via shared test harness
- [ ] Phase 3 — Pre-warmed pool eliminates cold start for demo load; pool replenishes correctly
- [ ] Phase 4 — Running VM state persisted to disk mid-execution
- [ ] Phase 5 — End-to-end demo: task killed, resumed from snapshot, correct final state
- [ ] Phase 6 — Orchid FSM can trigger checkpoint and resume via restore path
- [ ] Comparison doc against P07 (gVisor) complete — not two unrelated writeups
- [ ] INDEX.md links all artifacts

---

*Last updated: 2026-08-07 — Scoped and scaffolded, documentation brought in line with portfolio standard. No implementation started.*
