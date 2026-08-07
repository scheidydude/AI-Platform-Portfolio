# DESIGN-001 — MicroVM Execution Backend Architecture (Firecracker)

**Version:** 1.0
**Date:** 2026-08-07
**Author:** David Scheiderman
**Status:** Draft
**Project:** Project 08 — MicroVM Execution Backend with Checkpoint/Restore (Firecracker)

Requirements this design satisfies are specified in [SRS-001](../srs/SRS-001.md). See [ADR-001](../adr/ADR-001-reuse-p07-execution-contract.md), [ADR-002](../adr/ADR-002-small-warm-vm-pool.md), and [ADR-003](../adr/ADR-003-honest-cold-start-reporting.md) for the decisions behind this architecture.

---

## 1. Overview

Build a Firecracker-backed microVM execution layer as an alternative isolation backend to [Project 07's](../../../project-07-gvisor-sandbox/) gVisor approach, with the specific goal of demonstrating checkpoint/snapshot/restore for long-running agent tasks — directly evidencing "state management for long-running agent tasks, handling checkpoints, recovery, and resumption across failures." This is the harder, higher-signal of the two sandbox projects: not just isolation, but durable execution across failures.

## 2. Architecture

```
Orchid Agent (long-running task)
        │
        ▼
Execution API (same interface contract as Project 07)  [FR-2, ADR-001]
        │
        ▼
VM Pool Manager (new)                                    [FR-3, ADR-002]
        │  - maintains N pre-warmed Firecracker microVMs (N = 2-3 for demo)
        │  - assigns VM to incoming task
        │  - tracks VM state: warm / running / snapshotted
        ▼
Firecracker microVM (stripped kernel + Alpine rootfs)     [FR-1]
        │  - executes task
        │  - on checkpoint trigger: snapshot to disk (memory + device state)  [FR-4]
        ▼
Snapshot Store (local disk, NucBox)
        │  - on restore: new Firecracker process loads snapshot, resumes execution  [FR-5]
        ▼
Result / resumed task → Orchid task/result schema         [FR-6]
```

## 3. Phased Implementation

| Phase | Satisfies | Description |
|---|---|---|
| 1 — Minimal Boot | FR-1 | Stripped kernel + Alpine rootfs; boot via Firecracker API, measure cold start |
| 2 — Execution API Parity | FR-2 | Same request/response contract as Project 07's gVisor backend |
| 3 — VM Pool Manager | FR-3 | N pre-warmed idle VMs, assign on request, async replenish |
| 4 — Snapshot | FR-4 | Trigger Firecracker snapshot API mid-execution; persist memory + device state |
| 5 — Restore | FR-5 | Kill original process, load snapshot into new process, verify correct resumption |
| 6 — Orchid Integration | FR-6 | Wire checkpoint/restore into Orchid's lifecycle FSM |

Full phase-by-phase acceptance criteria live in `task_plan.md`; requirement-level acceptance criteria live in [SRS-001](../srs/SRS-001.md).

## 4. Deliverables for Portfolio

- Working demo: long-running task snapshotted, host killed, task resumed correctly — the single strongest artifact for the "checkpoints, recovery, resumption" evidence, worth a short recorded demo, not just a written description
- Cold-start and pool-latency numbers, documented honestly on real homelab hardware ([ADR-003](../adr/ADR-003-honest-cold-start-reporting.md))
- This architecture doc + a comparison write-up against [Project 07](../../../project-07-gvisor-sandbox/): isolation strength, overhead, cold-start, when to choose one over the other
- Interview-ready explanation of the snapshot/restore mechanism below "it just works" level — what's actually persisted (memory pages, device state) and why that's hard

## 5. Effort Estimate

2–3 weekends minimum for Phases 1–5. Phase 6 (Orchid FSM integration) is a further weekend, and is the piece most likely to reveal design friction worth writing about even if it's messy — document friction, don't hide it.
