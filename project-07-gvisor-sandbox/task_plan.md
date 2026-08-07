# P07 Task Plan — gVisor Sandboxed Execution

**Goal:** Harden Orchid's existing `ContainerRunner` isolation path with `runsc`, enforced resource ceilings, default-deny network egress, and per-execution syscall observability. (Revised 2026-08-07 — see "Blocking decision" note below, now resolved.)

**Depends on:** None. Sequenced before P08 (Firecracker) — P08 reuses this project's execution result contract.

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 0 — Recon | mostly complete | Confirm NucBox kernel/Docker version supports `runsc`; audit existing isolation surface (`ContainerRunner`/`WorkerResult`) — Traefik confirmation still open |
| 1 — Runtime Setup | in progress | Install/configure `runsc`; verify isolation via syscall-interception test |
| 2 — Hardened `ContainerRunner` | not started | Add `isolation.container_runtime`/`container_memory_mb`/`container_cpus` config; extend `WorkerResult` additively |
| 3 — Network Policy | not started | Default-deny egress; allowlist mode via Traefik |
| 4 — Verification Across Isolation Paths | not started | Confirm existing `WorkerResult` consumers unaffected; demo via `TesterAgent` |
| 5 — Observability | not started | Syscall log per task ID; summary in ccview |
| 6 — Multi-Tenant Quotas (stretch) | not started | Two concurrent tenants, independently enforced cgroup quotas |

---

## Phase 0 — Recon

- [x] Confirm `runsc` install path/version compatible with NucBox host kernel — `release-20260803.0`, confirmed against kernel `6.19.0-061900rc8-generic` via a working `--runtime=runsc` run (see `findings.md`)
- [x] Audit Orchid `TesterAgent` current modes and task/result schema shape — done; **found the real schema (`WorkerResult`/`TaskContext`) and integration surface (`ContainerRunner`) differ substantially from SRS-001/DESIGN-001/ADR-002's assumptions. See `findings.md` — blocks Phase 2/4 until resolved.**
- [ ] Confirm Traefik config location for later allowlist wiring — narrowed to two candidates, not yet confirmed which governs sandbox egress (see `findings.md`)
- [x] Install `runsc` on NucBox — installed via gVisor apt repo, version `release-20260803.0`, pinned in `findings.md`
- [ ] Define supported `language` values for the execution API's request shape and the sandbox base image(s) required for each — **superseded**: `ContainerRunner` runs one fixed image (`python:3.12-slim`) executing Orchid's own worker module, not user-selected-language snippets. Revisit after the Phase 2/4 architecture question below is resolved.
- [ ] Set default `timeout_s` and `memory_mb` values for the execution API — real gap confirmed: `ContainerRunner`'s `docker run` call has no `--memory`/`--cpus` flags at all today
- [x] Define a teardown/cleanup step for sandbox containers after each execution — `ContainerRunner` already runs with `--rm`; still need to verify no orphans on the timeout-kill path specifically (see `findings.md`)
- [x] Define a rollback plan for the `runsc` install — documented in `findings.md` (remove the `daemon.json` entry `runsc install` added, restart Docker); not yet exercised

### Blocking decision before Phase 1/2 proceed — RESOLVED 2026-08-07

Phase 0's schema audit found that Orchid already has a generic, config-driven isolation layer (`isolation.container_enabled` → `ContainerRunner`, `docker run` with no runtime/resource flags today) independent of any specific agent — not a `TesterAgent`-specific "mode" as SRS-001 FR-4 and ADR-002 originally assumed, and not a `{stdout, stderr, exit_code}` schema as SRS-001 FR-2 originally assumed (real schema is `WorkerResult{task_id, success, result, error, duration_s, cpu_seconds}`).

**Decision:** harden `ContainerRunner` + extend `WorkerResult` additively, rather than building a standalone "Sandbox Execution API." SRS-001, DESIGN-001, and ADR-002 have been revised accordingly (v1.1). See `findings.md` and ADR-002 for full detail.

## Phase 1 — Runtime Setup (Acceptance: `runsc` container runs and is verifiably isolated)

- [x] Install and configure `runsc` on NucBox as a secondary Docker runtime — done in Phase 0, `release-20260803.0`
- [x] `docker run --runtime=runsc` executes successfully alongside default runtime containers — verified with `hello-world`
- [ ] Isolation verified via at least one syscall-interception test, documented with output

## Phase 2 — Hardened `ContainerRunner` (Acceptance: `isolation.container_runtime=runsc` works with enforced limits)

- [ ] Add `isolation.container_runtime`, `isolation.container_memory_mb`, `isolation.container_cpus` config keys (default: unset/`runc`, unchanged behavior)
- [ ] Wire these into `ContainerRunner.run_task_isolated()`'s `docker run` invocation as `--runtime`, `--memory`, `--cpus`
- [ ] Execution exceeding the memory limit is killed, surfaces as a failed `WorkerResult` (`success=False`, `error` populated)
- [ ] Extend `WorkerResult` with optional `stdout`/`stderr`/`exit_code` fields (default unset) — additive only
- [ ] A known test task returns a correct `WorkerResult` when run under `--runtime=runsc` with limits applied

## Phase 3 — Network Policy (Acceptance: default-deny egress, explicit allowlist works)

- [ ] Default execution runs with `--network none` (verified via failed curl attempt inside container)
- [ ] Allowlisted execution can reach only specified domain(s), confirmed via test, routed through the confirmed Traefik config

## Phase 4 — Verification Across Isolation Paths (Acceptance: existing consumers unaffected, demo works)

- [ ] Existing `WorkerResult` consumers (`orchestrator.py`, `remote/worker_server.py`, `remote/dispatcher.py`, `worker_subprocess.py`) pass Orchid's existing test suite unmodified
- [ ] `TesterAgent` task run via `isolation.container_enabled` + `isolation.container_runtime: runsc` completes correctly, demonstrating the hardened path end-to-end

## Phase 5 — Observability (Acceptance: syscall trace available per execution)

- [ ] Each sandboxed execution has an associated syscall log retrievable by task ID
- [ ] At least a summary view visible in ccview or equivalent

## Phase 6 — Multi-Tenant Quotas (stretch)

- [ ] Two concurrent "tenants" demonstrated with independently enforced quotas
