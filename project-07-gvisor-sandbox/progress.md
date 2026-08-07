# P07 Progress Log

Implementation runs on the NucBox EVO X2 homelab host (Linux + `runsc`), via a Claude Code CLI session with this repo cloned there — confirmed as the actual environment 2026-08-07 (not the portfolio author's macOS dev machine, as originally assumed).

## Session log

### 2026-08-07 — Phase 0 recon + architecture revision

- Confirmed host state: Ubuntu 25.10, kernel `6.19.0-061900rc8-generic`, Docker 29.6.1, KVM ready, `dave` in `docker` group.
- Installed `runsc` (`release-20260803.0`) via the gVisor apt repo (David ran the privileged steps manually — Claude Code has no `sudo` on this host). Registered as a secondary Docker runtime and verified: `docker run --rm --runtime=runsc hello-world` ran clean.
- Audited the real Orchid codebase (`/home/dave/LocalAI/orchid`) for the `TesterAgent`/task-result-schema Phase 0 checklist item. **Found the original SRS-001/DESIGN-001/ADR-002 assumptions didn't match the real code:** `TesterAgent` isn't mode-dispatching, `verify_syntax_only` is a global prompt-injection config flag, and the real result schema is `WorkerResult{task_id, success, result, error, duration_s, cpu_seconds}` — not `{stdout, stderr, exit_code}`. Isolation is already generic infrastructure via `ContainerRunner`/`orchestrator.py:_run_task_isolated()`, independent of agent type, but its `docker run` call has no runtime/resource/network flags today.
- Presented the finding and two paths forward to David: harden `ContainerRunner` in place vs. build the originally-scoped standalone execution service. **Decision: harden `ContainerRunner`.** Revised SRS-001 (v1.1), DESIGN-001 (v1.1), ADR-002 (superseded in place, decision recorded), and `task_plan.md` Phases 2/4 to match. ADR-001/ADR-003 lightly edited for consistency (ADR-003 now also explicitly excludes `remote/worker_server.py`, an existing FastAPI service found during the same audit that binds `0.0.0.0`).
- Next entry point: Phase 1's syscall-interception test (not yet done — Phase 0/1 covered install + a basic `hello-world` run, not isolation verification), then Phase 2 (add `isolation.container_runtime`/`container_memory_mb`/`container_cpus` config to `ContainerRunner`).
