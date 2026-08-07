# ADR-002 — Harden `ContainerRunner` and Extend `WorkerResult`, Not a New Sandbox Service

**Status:** Accepted (supersedes prior decision below)
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

The original plan (see "Superseded decision" below) assumed Orchid's `TesterAgent` had a `verify_syntax_only` mode acting as a dispatch switch, and that a new mode could be added alongside it, returning results via a `{stdout, stderr, exit_code}`-shaped schema.

Phase 0 recon (2026-08-07, see `findings.md`) read the actual code and found a different picture:

- `verify_syntax_only` is a global boolean config flag (`agents.verify_syntax_only`) that injects a prompt instruction block into *any* agent's system prompt (`BaseAgent._verify_syntax_only_section()`). It is not a dispatch switch, and `TesterAgent` has no mode-branching logic to extend.
- Orchid already has a generic, agent-independent isolation layer: `orchestrator.py:_run_task_isolated()` selects between `ContainerRunner` (Docker) and `SubprocessRunner` (OS rlimits) based on `isolation.*` config, for any agent's task.
- `ContainerRunner`'s `docker run` invocation has no `--runtime`, `--memory`, `--cpus`, or `--network` flags today — it runs a fixed image (`python:3.12-slim`) with no resource ceiling beyond an application-level timeout.
- The real result schema is `WorkerResult{task_id, success, result, error, duration_s, cpu_seconds}`, not `{stdout, stderr, exit_code}`.

## Decision

Harden `ContainerRunner` directly:

1. Add `isolation.container_runtime` (default: unset → `runc`, unchanged behavior), `isolation.container_memory_mb`, and `isolation.container_cpus` config keys, wired into the existing `docker run` invocation as `--runtime`, `--memory`, `--cpus`.
2. Add `--network none` by default to that same invocation, with an allowlist mode per FR-3.
3. Extend `WorkerResult` with optional fields (`stdout`, `stderr`, `exit_code`, default unset) rather than introducing any parallel result type.

No new "Sandbox Execution API" service is built. No new `TesterAgent` mode is added — hardening applies to `ContainerRunner`, which any agent's task already goes through when `isolation.container_enabled` is set. `TesterAgent` is used only as the concrete demo vehicle for the portfolio write-up, not as an integration point in the code.

## Superseded Decision (v1.0, kept for record)

> `sandboxed_execution` is added as a new mode on `TesterAgent`, alongside `verify_syntax_only`, not as a replacement. The execution API's `{stdout, stderr, exit_code, duration_ms}` response is mapped into Orchid's existing task/result schema — no parallel result format is introduced.

This assumed a code shape (`TesterAgent` mode dispatch, `{stdout, stderr, exit_code}` schema) that does not exist in the real codebase. Superseded in full by the decision above.

## Rationale

- Hardening the mechanism Orchid already uses for isolation benefits every agent task run with `isolation.container_enabled=true`, not just `TesterAgent` — a strictly larger and more honest scope for the same amount of work.
- It is a more literal reading of the original intent behind reusing Orchid's schema (previously ADR-002, now folded into this one): extend the *actual* schema (`WorkerResult`) rather than a schema that was assumed but doesn't exist.
- Smaller diff, smaller surface area, no new service to secure, deploy, or explain in an interview as a second thing that could fail.

## Consequences

- `ContainerRunner`'s existing callers (`subprocess_runner.py`, `orchestrator.py`, `remote/worker_server.py`) must continue to work unmodified when `isolation.container_runtime` is unset — this is the regression bar (SRS-001 FR-4 acceptance criteria).
- The portfolio demo path is: enable `isolation.container_enabled` + `isolation.container_runtime: runsc` for a project, run a `TesterAgent` task, and show the resulting `WorkerResult` plus the syscall-interception proof — not a standalone API demo.
- `remote/worker_server.py` (binds `0.0.0.0`) is explicitly not part of this project's demo path — see ADR-003. If gVisor hardening is ever exposed through it, that reopens the auth/exposure question ADR-003 currently closes.
