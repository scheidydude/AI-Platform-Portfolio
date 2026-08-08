# P07 Task Plan — gVisor Sandboxed Execution

**Goal:** Harden Orchid's existing `ContainerRunner` isolation path with `runsc`, enforced resource ceilings, default-deny network egress, and per-execution syscall observability. (Revised 2026-08-07 — see "Blocking decision" note below, now resolved.)

**Depends on:** None. Sequenced before P08 (Firecracker) — P08 reuses this project's execution result contract.

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 0 — Recon | complete | Confirm NucBox kernel/Docker version supports `runsc`; audit existing isolation surface (`ContainerRunner`/`WorkerResult`); confirm egress mechanism |
| 1 — Runtime Setup | complete | Install/configure `runsc`; verify isolation via syscall-interception test |
| 2 — Hardened `ContainerRunner` | complete | Add `isolation.container_runtime`/`container_memory_mb`/`container_cpus` config; extend `WorkerResult` additively |
| 3 — Network Policy | complete | Default-deny egress (`--network none`); allowlist via a new Squid forward-proxy sidecar (ADR-004) |
| 4 — Verification Across Isolation Paths | complete | Confirm existing `WorkerResult` consumers unaffected; demo via `TesterAgent` — found & fixed ContainerRunner was never functional |
| 5 — Observability | complete | Syscall log per task ID; summary flows into PM Dashboard's data source (`ccview` doesn't exist) |
| 6 — Multi-Tenant Quotas (stretch) | not started | Two concurrent tenants, independently enforced cgroup quotas |

---

## Phase 0 — Recon

- [x] Confirm `runsc` install path/version compatible with NucBox host kernel — `release-20260803.0`, confirmed against kernel `6.19.0-061900rc8-generic` via a working `--runtime=runsc` run (see `findings.md`)
- [x] Audit Orchid `TesterAgent` current modes and task/result schema shape — done; **found the real schema (`WorkerResult`/`TaskContext`) and integration surface (`ContainerRunner`) differ substantially from SRS-001/DESIGN-001/ADR-002's assumptions. See `findings.md` — blocks Phase 2/4 until resolved.**
- [x] Confirm Traefik config location for later allowlist wiring — **resolved, and the premise was wrong**: Traefik on this host is ingress-only (external HTTPS → internal services), confirmed via `systemctl status traefik` + reading its static and dynamic configs directly. Neither candidate does egress. See `findings.md` — Phase 3's allowlist mechanism needs to be new infrastructure, not "wire into Traefik."
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
- [x] Isolation verified via at least one syscall-interception test, documented with output — two tests (`uname`/`/proc/version` kernel-identity divergence, `io_uring_setup` ENOSYS under `runsc` vs. success on the raw host kernel), see `findings.md` and `scripts/verify_isolation.sh`

## Phase 2 — Hardened `ContainerRunner` (Acceptance: `isolation.container_runtime=runsc` works with enforced limits)

- [x] Add `isolation.container_runtime`, `isolation.container_memory_mb`, `isolation.container_cpus` config keys (default: unset/`runc`, unchanged behavior)
- [x] Wire these into `ContainerRunner.run_task_isolated()`'s `docker run` invocation as `--runtime`, `--memory`, `--cpus`
- [x] Execution exceeding the memory limit is killed, surfaces as a failed `WorkerResult` (`success=False`, `error` populated, now also `exit_code=137`) — proven with `scripts/probe_memory_limit.py` under `--runtime=runsc --memory=64m`
- [x] Extend `WorkerResult` with optional `stdout`/`stderr`/`exit_code` fields (default unset) — additive only, unit-tested
- [x] A known test task returns a correct `WorkerResult` when run under `--runtime=runsc` with limits applied — verified at the Docker level directly (see `findings.md`); a full `orchid.worker_subprocess` ReAct-loop run is Phase 4's job, not Phase 2's

**Status:** Complete. Committed to the `p07-gvisor-hardening` branch in the Orchid repo (`0eaac75`) — not merged to `main`, that's David's call. Full ~1800-test suite run was aborted (pre-existing, unrelated MCP-subprocess leak in Orchid's own tests, not a regression — see `findings.md`); verification rests on the targeted unit tests, the 42/43 broader consumer subset, and real Docker+`runsc` end-to-end proof.

## Phase 3 — Network Policy (Acceptance: default-deny egress, explicit allowlist works)

**Blocking decision (resolved 2026-08-07):** Traefik on this host is ingress-only, confirmed in Phase 0 — SRS-001 FR-3's "allowlist via Traefik" premise was wrong. David chose a dedicated Squid forward-proxy sidecar over DNS-filtering and iptables/nftables (ADR-004). Implemented and verified.

- [x] Decide the allowlist mechanism — Squid sidecar (ADR-004); SRS-001/DESIGN-001 updated to v1.2
- [x] Default execution runs with `--network none` — verified via real DNS-resolution failure inside the container (deliberate behavior change from the prior no-flag/default-bridge behavior)
- [x] Allowlisted execution can reach only specified domain(s), confirmed via test — five live tests: default-deny, allowlisted HTTP (200), non-allowlisted HTTP (403), allowlisted/non-allowlisted HTTPS via CONNECT, and the full set again composed with `--runtime=runsc`

**Status:** Complete. Committed to `p07-gvisor-hardening` (`f7e0dbf`). Found and fixed a real gVisor limitation along the way (can't resolve Docker's embedded DNS on a user-defined network under `runsc`; worked around with IP-based addressing) — see `findings.md`, directly useful for the gVisor-vs-Firecracker comparison deliverable.

## Phase 4 — Verification Across Isolation Paths (Acceptance: existing consumers unaffected, demo works)

- [x] Existing `WorkerResult` consumers (`orchestrator.py`, `remote/worker_server.py`, `remote/dispatcher.py`, `worker_subprocess.py`) pass Orchid's existing test suite unmodified — checked every relevant test file individually (avoiding the leaky full suite); 8 pre-existing failures across 3 files, all confirmed identical on `main`, zero regressions
- [x] `TesterAgent` task run via `isolation.container_enabled` + `isolation.container_runtime: runsc` completes correctly, demonstrating the hardened path end-to-end — real live demo: `success=True`, real LLM call, real pytest run, under `runsc` + 512MB memory cap + network locked to one allowlisted domain

**Status:** Complete. Committed to `p07-gvisor-hardening` (`9beaea5`). Found and fixed three pre-existing bugs that meant `ContainerRunner` had never actually worked for any task before this — see `findings.md`. Not scope creep: fixing them was required to satisfy this phase's own acceptance criterion.

## Phase 5 — Observability (Acceptance: syscall trace available per execution)

- [x] Each sandboxed execution has an associated syscall log retrievable by task ID — `~/.orchid/sandbox_syscall_logs/<task_id>/`, verified live through the real `ContainerRunner` code path
- [x] At least a summary view visible in ccview or equivalent — `ccview` doesn't exist in this codebase (checked); wired `syscall_summary` into `task_metrics.jsonl` instead, the real file the PM Dashboard's existing `/get_metrics` endpoint already serves. No dedicated dashboard UI column added — out of scope for this phase, flagged as a follow-up

**Status:** Complete. Committed to `p07-gvisor-hardening` (`41fea7a`). Needed a Docker daemon config correction along the way (`sudo runsc install -- --allow-flag-override`, not a hand-edited `daemon.json` — see `findings.md`) and a full parser rewrite once the real gVisor strace log format was available to verify against (first draft guessed wrong).

## Phase 6 — Multi-Tenant Quotas (stretch)

- [ ] Two concurrent "tenants" demonstrated with independently enforced quotas
