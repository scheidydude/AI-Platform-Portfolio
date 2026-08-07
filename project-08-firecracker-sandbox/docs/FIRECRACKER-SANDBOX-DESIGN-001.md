# FIRECRACKER-SANDBOX-DESIGN-001

**Project:** MicroVM Execution Backend with Checkpoint/Restore (Firecracker)
**Portfolio Track:** AI Platform Portfolio — Agentic Systems / Durable Execution
**Target Use Case:** Proof-of-work for Staff+ Infrastructure roles requiring microVM isolation, state management, and checkpoint/recovery for long-running agent tasks
**Status:** Scoped, not started
**Depends On:** GVISOR-SANDBOX-DESIGN-001 (shared execution API shape, sequencing)
**Owner:** David Scheiderman
**Implementation Agent:** Claude Code CLI

---

## 1. Purpose

Build a Firecracker-backed microVM execution layer as an alternative isolation backend to the gVisor project, with the specific goal of demonstrating checkpoint/snapshot/restore for long-running agent tasks — directly evidencing "state management for long-running agent tasks, handling checkpoints, recovery, and resumption across failures."

This is the harder, higher-signal of the two sandbox projects. It's scoped separately from gVisor because it demonstrates a different capability: not just isolation, but durable execution across failures.

## 2. Background / Motivation

Firecracker (AWS Lambda/Fargate's underlying microVM tech) offers stronger isolation than container-based sandboxing and native snapshot/restore of a running VM's full state. For an agentic platform, this maps directly to the hard problem of resuming a long-running agent task after a host failure, deploy, or restart — something Orchid's current FSM does not yet solve at the process/VM level.

## 3. Goals

- Boot a minimal Firecracker microVM (<200ms cold start) capable of running agent task code
- Maintain a pre-warmed VM pool to avoid cold-start latency on demand
- Snapshot a running microVM mid-execution to disk
- Restore a microVM from snapshot on a different host process (simulating recovery from failure)
- Demonstrate an end-to-end scenario: long-running Orchid agent task snapshotted mid-execution, host process killed, task resumed from snapshot with correct state
- Provide the same execution API shape as the gVisor project so the two are interchangeable backends from Orchid's perspective

## 4. Non-Goals

- Not building a general-purpose FaaS platform
- Not covering live migration between physical hosts (single NucBox host only)
- Not optimizing cold-start below what's achievable on the AMD ROCm homelab hardware — document actual numbers rather than chasing a target

## 5. Architecture

```
Orchid Agent (long-running task)
        │
        ▼
Execution API (same interface contract as gVisor project)
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

## 6. Phased Implementation

### Phase 1 — Minimal Boot (Acceptance: microVM boots and runs a task in <200ms)
- Build stripped kernel + Alpine (or similar) rootfs image
- Boot via Firecracker API, confirm cold-start timing
- Acceptance criteria:
  - [ ] MicroVM boots and executes a trivial script, cold start measured and documented
  - [ ] Boot time is under 200ms or documented with explanation if not (real hardware numbers > target chasing)

### Phase 2 — Execution API Parity (Acceptance: same request/response contract as gVisor project)
- Implement the same `{code, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code}` contract
- Acceptance criteria:
  - [ ] A test harness can submit the same request to either the gVisor or Firecracker backend and get equivalent results

### Phase 3 — VM Pool Manager (Acceptance: pre-warmed pool eliminates cold start for demo load)
- Maintain N idle warm VMs, assign on request, replenish pool asynchronously
- Acceptance criteria:
  - [ ] Demonstrated request latency with pool vs. without (cold boot), documented difference
  - [ ] Pool correctly replenishes after VM is consumed

### Phase 4 — Snapshot (Acceptance: running VM state can be persisted to disk)
- Trigger Firecracker's snapshot API mid-execution
- Persist memory + device state to local disk
- Acceptance criteria:
  - [ ] A VM executing a multi-step task can be snapshotted at an arbitrary point
  - [ ] Snapshot file exists and is documented (size, contents description)

### Phase 5 — Restore (Acceptance: task resumes correctly from snapshot after host process kill)
- Kill the original Firecracker process
- Load snapshot into a new Firecracker process
- Verify task resumes and completes correctly (not restarted from scratch)
- Acceptance criteria:
  - [ ] End-to-end demo: task killed mid-execution, resumed from snapshot, completes with correct final state
  - [ ] Resumed task output matches what an uninterrupted run would produce (verified via deterministic test task)

### Phase 6 — Orchid Integration (Acceptance: Orchid's FSM can trigger checkpoint/restore)
- Wire snapshot trigger into Orchid's lifecycle FSM (e.g. on `CHECKPOINT` state or CentralBotManager-issued signal)
- Wire restore into task resumption path
- Acceptance criteria:
  - [ ] Orchid can issue a checkpoint command that results in a snapshot
  - [ ] Orchid can resume a previously checkpointed task via the restore path, using existing task metrics/result schema

## 7. Deliverables for Portfolio

- Working demo: long-running task snapshotted, host killed, task resumed correctly — this is the single strongest artifact for the "checkpoints, recovery, resumption" JD bullet and worth a short recorded demo, not just a written description
- Cold-start and pool-latency numbers, documented honestly (real homelab hardware, not idealized)
- Architecture diagram (this doc) + comparison write-up against the gVisor project: isolation strength, overhead, cold-start, when you'd choose one over the other
- Interview-ready explanation of the snapshot/restore mechanism at a level below "it just works" — what's actually being persisted (memory pages, device state) and why that's hard

## 8. Effort Estimate

2–3 weekends minimum for Phases 1–5. Phase 6 (Orchid FSM integration) is a further weekend, and is the piece most likely to reveal design friction worth writing about even if it's messy — document friction, don't hide it.

## 9. Handover Notes for Claude Code CLI

- Sequence after GVISOR-SANDBOX-DESIGN-001 — reuse its execution API contract rather than designing a new one
- Expect Phase 4/5 (snapshot/restore) to be the highest-risk phase on this specific hardware (AMD host, ROCm drivers potentially interacting with KVM/Firecracker) — budget debugging time here, and document any host-specific quirks encountered, since that's genuine signal for an interview
- Keep VM pool size small for the demo (2–3 warm VMs) — this is a portfolio proof, not a load test
- Output of this project should produce a comparison doc against the gVisor backend as a final artifact, not just two unrelated writeups
