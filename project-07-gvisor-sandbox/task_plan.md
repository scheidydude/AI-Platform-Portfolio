# P07 Task Plan — gVisor Sandboxed Execution

**Goal:** Integrate `runsc` as an opt-in isolated execution mode for Orchid's `TesterAgent`, with enforced resource ceilings, default-deny network egress, and per-execution syscall observability.

**Depends on:** None. Sequenced before P08 (Firecracker) — P08 reuses this project's execution API contract.

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 0 — Recon | not started | Confirm NucBox kernel/Docker version supports `runsc`; audit existing `TesterAgent` and task/result schema |
| 1 — Runtime Setup | not started | Install/configure `runsc`; verify isolation via syscall-interception test |
| 2 — Execution API | not started | Build execution service; enforce timeout + memory limit |
| 3 — Network Policy | not started | Default-deny egress; allowlist mode via Traefik |
| 4 — Orchid Integration | not started | `sandboxed_execution` mode on `TesterAgent`; results in PM Dashboard |
| 5 — Observability | not started | Syscall log per task ID; summary in ccview |
| 6 — Multi-Tenant Quotas (stretch) | not started | Two concurrent tenants, independently enforced cgroup quotas |

---

## Phase 0 — Recon

- [ ] Confirm `runsc` install path/version compatible with NucBox host kernel
- [ ] Audit Orchid `TesterAgent` current modes and task/result schema shape
- [ ] Confirm Traefik config location for later allowlist wiring

## Phase 1 — Runtime Setup (Acceptance: `runsc` container runs and is verifiably isolated)

- [ ] Install and configure `runsc` on NucBox as a secondary Docker runtime
- [ ] `docker run --runtime=runsc` executes successfully alongside default runtime containers
- [ ] Isolation verified via at least one syscall-interception test, documented with output

## Phase 2 — Execution API (Acceptance: agent can submit code, get bounded result)

- [ ] Build execution service: `{code, language, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code, duration_ms}`
- [ ] Service rejects/kills execution exceeding timeout, returns structured error
- [ ] Service rejects/kills execution exceeding memory limit, returns structured error
- [ ] Successful execution returns correct stdout/stderr/exit_code for a known test script

## Phase 3 — Network Policy (Acceptance: default-deny egress, explicit allowlist works)

- [ ] Default execution has zero network access (verified via failed curl attempt inside sandbox)
- [ ] Allowlisted execution can reach only specified domain(s), confirmed via test

## Phase 4 — Orchid Integration (Acceptance: TesterAgent can invoke sandboxed execution as a mode)

- [ ] `TesterAgent` configurable to run in `sandboxed_execution` mode
- [ ] Results appear in PM Dashboard using existing task metrics display, no schema break

## Phase 5 — Observability (Acceptance: syscall trace available per execution)

- [ ] Each sandboxed execution has an associated syscall log retrievable by task ID
- [ ] At least a summary view visible in ccview or equivalent

## Phase 6 — Multi-Tenant Quotas (stretch)

- [ ] Two concurrent "tenants" demonstrated with independently enforced quotas
