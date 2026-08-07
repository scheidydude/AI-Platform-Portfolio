# P08 Task Plan — Firecracker MicroVM Execution Backend

**Goal:** Build a Firecracker-backed microVM execution layer with checkpoint/snapshot/restore, matching Project 07's execution API contract, and demonstrate task resumption across a simulated host failure.

**Depends on:** [Project 07](../project-07-gvisor-sandbox/) — reuse its execution API contract rather than designing a new one. Sequence after P07.

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 0 — Recon | not started | Confirm KVM availability on NucBox; review Firecracker version compatibility with AMD/ROCm host |
| 1 — Minimal Boot | not started | Stripped kernel + Alpine rootfs; boot via Firecracker API, measure cold start |
| 2 — Execution API Parity | not started | Same `{code, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code}` contract as P07 |
| 3 — VM Pool Manager | not started | N pre-warmed idle VMs, assign on request, async replenish |
| 4 — Snapshot | not started | Trigger Firecracker snapshot API mid-execution; persist memory + device state to disk |
| 5 — Restore | not started | Kill original process, load snapshot into new process, verify correct resumption |
| 6 — Orchid Integration | not started | Wire checkpoint/restore into Orchid's lifecycle FSM |

---

## Phase 0 — Recon

- [ ] Confirm KVM is available and enabled on NucBox (AMD host)
- [ ] Confirm Firecracker version/compatibility with host kernel and ROCm drivers coexisting
- [ ] Review P07's finalized execution API contract before starting Phase 2

## Phase 1 — Minimal Boot (Acceptance: microVM boots and runs a task in <200ms)

- [ ] Build stripped kernel + Alpine (or similar) rootfs image
- [ ] Boot via Firecracker API, confirm cold-start timing
- [ ] Boot time under 200ms, or documented with explanation if not (real hardware numbers, not target chasing)

## Phase 2 — Execution API Parity (Acceptance: same contract as P07)

- [ ] Implement `{code, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code}`
- [ ] Test harness can submit the same request to either backend (gVisor/Firecracker) and get equivalent results

## Phase 3 — VM Pool Manager (Acceptance: pre-warmed pool eliminates cold start for demo load)

- [ ] Maintain N idle warm VMs, assign on request, replenish pool asynchronously
- [ ] Demonstrated request latency with pool vs. without (cold boot), documented difference
- [ ] Pool correctly replenishes after VM is consumed

## Phase 4 — Snapshot (Acceptance: running VM state can be persisted to disk)

- [ ] Trigger Firecracker's snapshot API mid-execution
- [ ] Persist memory + device state to local disk
- [ ] A VM executing a multi-step task can be snapshotted at an arbitrary point
- [ ] Snapshot file exists and is documented (size, contents description)

## Phase 5 — Restore (Acceptance: task resumes correctly from snapshot after host process kill)

- [ ] Kill the original Firecracker process
- [ ] Load snapshot into a new Firecracker process
- [ ] End-to-end demo: task killed mid-execution, resumed from snapshot, completes with correct final state
- [ ] Resumed task output matches an uninterrupted run (verified via deterministic test task)

## Phase 6 — Orchid Integration (Acceptance: Orchid's FSM can trigger checkpoint/restore)

- [ ] Wire snapshot trigger into Orchid's lifecycle FSM (e.g. `CHECKPOINT` state or CentralBotManager-issued signal)
- [ ] Wire restore into task resumption path
- [ ] Orchid can issue a checkpoint command resulting in a snapshot
- [ ] Orchid can resume a previously checkpointed task via the restore path, using existing task metrics/result schema

## Final Deliverable

- [ ] Comparison doc against the gVisor backend (P07): isolation strength, overhead, cold-start, when to choose one over the other — not two unrelated writeups
