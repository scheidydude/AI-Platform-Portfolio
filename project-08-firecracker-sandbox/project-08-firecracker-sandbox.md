# Project 08 — MicroVM Execution Backend with Checkpoint/Restore (Firecracker)

**Skill area:** MicroVM isolation · durable execution · state checkpoint/recovery
**Format:** Infrastructure integration build
**Estimated duration:** 2–3 weekends (Phases 1–5), +1 weekend for Phase 6
**Status:** Scoped, not started
**Depends on:** [Project 07 — gVisor Sandbox](../project-07-gvisor-sandbox/) (shared execution API shape, sequencing)

---

## Overview

Builds a Firecracker-backed microVM execution layer as an alternative isolation backend to [Project 07's](../project-07-gvisor-sandbox/) gVisor approach, with the specific goal of demonstrating checkpoint/snapshot/restore for long-running agent tasks. This is the harder, higher-signal of the two sandbox projects: it demonstrates not just isolation, but durable execution across failures — directly evidencing "state management for long-running agent tasks, handling checkpoints, recovery, and resumption across failures," a named requirement in Staff+ infrastructure roles.

Firecracker offers stronger isolation than container-based sandboxing plus native snapshot/restore of a running VM's full state. For Orchid, this maps to resuming a long-running agent task after a host failure, deploy, or restart — something Orchid's current FSM does not yet solve at the process/VM level.

Full design source: [`docs/design/DESIGN-001.md`](./docs/design/DESIGN-001.md). Requirements: [`docs/srs/SRS-001.md`](./docs/srs/SRS-001.md). Full artifact index: [`INDEX.md`](./INDEX.md).

---

## Goals

- Boot a minimal Firecracker microVM (<200ms cold start) capable of running agent task code
- Maintain a pre-warmed VM pool to avoid cold-start latency on demand
- Snapshot a running microVM mid-execution to disk
- Restore a microVM from snapshot on a different host process (simulating recovery from failure)
- Demonstrate end-to-end: long-running Orchid agent task snapshotted mid-execution, host process killed, task resumed from snapshot with correct state
- Provide the same execution API shape as Project 07 so the two backends are interchangeable from Orchid's perspective

## Non-Goals

- Not building a general-purpose FaaS platform
- Not covering live migration between physical hosts (single NucBox host only)
- Not optimizing cold-start below what's achievable on the AMD ROCm homelab hardware — document actual numbers rather than chasing a target

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 1 — Minimal Boot | not started | Stripped kernel + Alpine rootfs; boot via Firecracker API, measure cold start |
| 2 — Execution API Parity | not started | Same request/response contract as Project 07's gVisor backend |
| 3 — VM Pool Manager | not started | N pre-warmed idle VMs, assign on request, async replenish |
| 4 — Snapshot | not started | Trigger Firecracker snapshot API mid-execution; persist memory + device state |
| 5 — Restore | not started | Kill original process, load snapshot into new process, verify correct resumption |
| 6 — Orchid Integration | not started | Wire checkpoint/restore into Orchid's lifecycle FSM |

See [`docs/design/DESIGN-001.md`](./docs/design/DESIGN-001.md) for full phase-by-phase acceptance criteria.

---

## Architecture

```
Orchid Agent (long-running task)
        │
        ▼
Execution API (same interface contract as Project 07 / gVisor)
        │
        ▼
VM Pool Manager (new)
        │  - maintains N pre-warmed Firecracker microVMs
        │  - assigns VM to incoming task
        │  - tracks VM state: warm / running / snapshotted
        ▼
Firecracker microVM (stripped kernel + Alpine rootfs)
        │  - executes task
        │  - on checkpoint trigger: snapshot to disk (memory + device state)
        ▼
Snapshot Store (local disk, NucBox)
        │  - on restore: new Firecracker process loads snapshot, resumes execution
        ▼
Result / resumed task → Orchid task/result schema
```

---

## Deliverables for Portfolio

- Working demo: long-running task snapshotted, host killed, task resumed correctly — recorded, not just described
- Cold-start and pool-latency numbers, documented honestly (real homelab hardware, not idealized)
- Architecture diagram + comparison write-up against [Project 07](../project-07-gvisor-sandbox/): isolation strength, overhead, cold-start, when to choose one over the other
- Interview-ready explanation of the snapshot/restore mechanism below "it just works" level — what's persisted (memory pages, device state) and why that's hard

---

## Execution Environment

Requires Linux with KVM (Firecracker's hypervisor dependency) — does not run on the portfolio author's macOS dev machine. Implementation happens on the NucBox EVO X2 homelab host (AMD, ROCm drivers present) via a Claude Code CLI session run directly there. Phases 4/5 (snapshot/restore) are flagged in the source design doc as highest-risk on this specific hardware — budget debugging time and document any host-specific quirks encountered, as that is genuine interview signal.
