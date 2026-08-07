# P07 Handoff — gVisor Sandboxed Execution

**Current state:** Phase 1 complete. `runsc` installed and verified on the NucBox; syscall-interception isolation proven and documented. Architecture revised 2026-08-07 after Phase 0 recon found the original plan's assumptions about Orchid's codebase were wrong — see below.

**Where this runs:** NucBox EVO X2 (Linux, existing Docker/Traefik stack). Claude Code sessions in this repo run directly on that host — confirmed 2026-08-07. Claude Code has no `sudo` here; privileged steps (installs, daemon config) must be handed to David to run manually. Docker commands need `sg docker -c '...'` (or a fresh login shell) since group membership doesn't carry into new tool-call subprocesses.

**Exact next action:** Phase 2 — harden `ContainerRunner`. Add `isolation.container_runtime`/`isolation.container_memory_mb`/`isolation.container_cpus` config keys and wire them into `ContainerRunner.run_task_isolated()`'s `docker run` invocation as `--runtime`/`--memory`/`--cpus`; extend `WorkerResult` with optional `stdout`/`stderr`/`exit_code` fields. See `task_plan.md` Phase 2 and SRS-001 FR-2/FR-4.

**Sequencing note:** This project should be completed (at minimum through Phase 4) before starting [Project 08 — Firecracker](../project-08-firecracker-sandbox/), which depends on this project's execution result contract (`WorkerResult`, extended additively — not the originally-planned `{stdout, stderr, exit_code}` standalone contract; P08's docs will need a matching update once P07 Phase 2 lands).

**Architecture revision (2026-08-07 — read this before touching Phase 2+):**
Orchid's real codebase doesn't match what the original design docs assumed. `TesterAgent` is a prompt-driven ReAct agent, not mode-dispatching; `verify_syntax_only` is a global config flag that injects prompt text, not a per-task mode. The real integration point is `ContainerRunner` (`orchid/container_runner.py`) — already generic, agent-independent isolation infrastructure used via `isolation.container_enabled`, but its `docker run` call has no `--runtime`/`--memory`/`--cpus`/`--network` flags today. The real result schema is `WorkerResult{task_id, success, result, error, duration_s, cpu_seconds}` in `orchid/worker_protocol.py`.

**Decision made:** harden `ContainerRunner` in place and extend `WorkerResult` additively, rather than building a new standalone execution service. SRS-001, DESIGN-001, ADR-002 (and lightly, ADR-001/ADR-003) have been revised to match — read `findings.md` for the full audit before starting Phase 2, and ADR-002 for the decision record.

**Gotchas to expect:**
- `ContainerRunner` runs one fixed image (`python:3.12-slim`) executing Orchid's own `orchid.worker_subprocess` module — it does not run arbitrary user-selected-language code snippets. Don't reintroduce a `language` field into any new config/schema.
- `remote/worker_server.py` is an existing FastAPI service that binds `0.0.0.0` for distributed task execution — it is explicitly out of scope as an entry point for sandboxed execution (ADR-003). Don't wire gVisor hardening through it.
- Extend `WorkerResult` additively only (optional fields, default unset) — do not introduce a parallel result type or change existing field meanings. `orchestrator.py`, `remote/worker_server.py`, `remote/dispatcher.py`, and `worker_subprocess.py` all consume it today and must keep working unmodified.
- Docker's default seccomp profile blocks some syscalls (e.g. `io_uring_setup`) independently of the runtime — don't mistake a seccomp-level `EPERM` for gVisor-level `ENOSYS` when testing isolation further; see `scripts/verify_isolation.sh` for how to isolate the two.
