# P07 Findings

Research notes and decisions, accumulated as the project progresses.

## 2026-08-07 — Phase 0 recon (partial, host state)

Ran directly on the NucBox (Claude Code CLI has no `sudo` — privileged steps below must be run by David manually).

- **Host:** `dave-NucBox-EVO-X2`, Ubuntu 25.10 (Questing Quokka), kernel `6.19.0-061900rc8-generic` (mainline RC build, not a stock Ubuntu kernel — worth re-checking `runsc` compatibility against this specific kernel, not just "Ubuntu 25.10" in general).
- **Docker:** 29.6.1 installed and running.
- **`runsc`:** not installed (`command not found`). Needs install — see below.
- **KVM:** `/dev/kvm` present, `kvm_amd` + `kvm` modules loaded. Good sign for P08 (Firecracker) as well — no separate KVM enablement work needed.
- **Docker group:** `dave` is a member of the `docker` group (`getent group docker` → `docker:x:980:dave`), but the current shell session predates that membership — `docker ps` fails with a permission error until the group takes effect. Not a real blocker: fixable with `newgrp docker`, a new shell, or re-login. If it's still failing when Phase 1 work starts, check this first before assuming a real permissions problem.

### Needed: install `runsc` (run manually, requires sudo)

Official gVisor apt install for Ubuntu/Debian:

```bash
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
sudo apt-get update
sudo apt-get install -y runsc
```

Then register it as a secondary Docker runtime (per ADR-001 — do not replace the default runtime):

```bash
sudo runsc install    # patches /etc/docker/daemon.json to add the runsc runtime entry
sudo systemctl restart docker
```

Verify:

```bash
runsc --version
docker run --rm --runtime=runsc hello-world
docker ps -a --filter runtime=runsc   # confirm no leftover containers after the test
```

## 2026-08-07 — `runsc` install verified

David ran the install commands above manually. Verified:

- `runsc --version` → `release-20260803.0`, spec `1.2.1`
- `docker run --rm --runtime=runsc hello-world` → ran clean, printed the standard "Hello from Docker!" message
- `dave`'s `docker` group membership is now active in a fresh shell (`newgrp docker`) — `docker ps` works without `sudo`

Kernel compatibility (`6.19.0-061900rc8-generic`) is confirmed empirically by the successful `runsc`-runtime container run above — no separate compatibility check needed beyond this.

Rollback, if ever needed: remove the `runsc` entry `runsc install` added to `/etc/docker/daemon.json`, then `sudo systemctl restart docker`. Not yet tested — treat as unverified until actually exercised once.

## 2026-08-07 — Orchid `TesterAgent` / task-result-schema audit (major finding — design assumptions were wrong)

Orchid repo found at `/home/dave/LocalAI/orchid`. This audit was a Phase 0 checklist item ("audit Orchid `TesterAgent` current modes and task/result schema shape") — the real code differs substantially from what SRS-001 and DESIGN-001 assumed, written before this repo was accessible.

**`TesterAgent` (`orchid/agents/tester.py`) is a prompt-driven ReAct-loop LLM agent, not a mode-dispatching execution service.** It's a thin `BaseAgent` subclass with a system prompt telling the model to run tests via its allowed tools (`bash`, `read_file`, etc.) and report a JSON "Final Answer" as free text. There is no code branch resembling `if mode == "sandboxed_execution"`.

**`verify_syntax_only` is a global boolean config flag** (`agents.verify_syntax_only` in `orchid.defaults.yaml`, default `false`), not a per-task "mode" parameter. When true, `BaseAgent._verify_syntax_only_section()` (in `orchid/agents/base.py`) appends an instruction block to *any* agent's system prompt telling it to run `py_compile`/`node --check` instead of the real test suite. It's prompt-injection, not a dispatch switch — ADR-002's "additive mode alongside `verify_syntax_only`" framing doesn't map onto how this actually works.

**The real task/result schema is `WorkerResult`** (`orchid/worker_protocol.py`):
```python
@dataclass
class WorkerResult:
    task_id: str
    success: bool
    result: str = ""
    error: str = ""
    duration_s: float = 0.0
    cpu_seconds: float = 0.0
```
Not `{stdout, stderr, exit_code}` as SRS-001/DESIGN-001 assumed. `TaskContext` (the request side) carries `task_id, task_description, session_context, agent_type, model_key, project_dir, injection_queue_path` — also not `{code, language, timeout_s, memory_mb, network}`.

**Isolation is already a generic, config-driven property of task execution — not agent-specific.** `orchestrator.py:_run_task_isolated()` picks an isolation strategy per `isolation.*` config keys, independent of which agent type is running:
- `isolation.container_enabled: true` → `ContainerRunner` (`orchid/container_runner.py`) runs the whole agent worker subprocess inside `docker run --rm -i -w /orchid python:3.12-slim python -m orchid.worker_subprocess`, piping `TaskContext` in via stdin and reading `WorkerResult` back over stdout. **No `--runtime` flag, no `--memory`/`--cpus`/`--network` flags today** — plain default-runtime Docker, unconstrained.
- `isolation.container_enabled: false` → `SubprocessRunner` uses a pre-forked `WorkerPool` of plain OS subprocesses, applying **rlimits** (`RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NOFILE`) from `isolation.resource_limits` config in `_apply_resource_limits()`/`_resource_preexec()`. This is Orchid's existing (non-container) resource-ceiling mechanism.
- There's also `orchid/remote/worker_server.py` — an existing FastAPI service (`/task` endpoint, binds `0.0.0.0:$ORCHID_WORKER_PORT` default 8001) that accepts a `RemoteTaskRequest{task_context_json, timeout_s}` and dispatches to a runner, for distributed multi-node execution. Structurally this is close to what DESIGN-001 imagined as a "thin HTTP execution service" — except it isolates an entire agent task, not an arbitrary code/command string, and it already binds all interfaces, not host-local (worth a security note if this is ever considered as the P07 wiring point — contradicts ADR-003's host-local assumption if reused as-is).

**Implication for the plan:** The natural integration point for gVisor is `ContainerRunner`, not a new "Sandbox Execution API" HTTP service and not a new `TesterAgent` mode. Concretely: add `--runtime=runsc` (config-gated, per ADR-001) and real resource-limit flags (`--memory`, `--cpus`, `--network none` + allowlist proxy) to the `docker run` invocation in `container_runner.py`, and extend `WorkerResult` additively (e.g. optional `stdout`/`stderr`/`exit_code` fields, defaulting to unset) rather than inventing a parallel schema — this is actually *more* consistent with ADR-002's "reuse the existing schema" intent than the original design's imagined new API, and it benefits every agent run through `isolation.container_enabled`, not just `TesterAgent`. This also means the "language" field in the original request-shape assumption doesn't apply — `ContainerRunner` runs a fixed `python:3.12-slim` image executing Orchid's own worker module, not arbitrary user-selected-language snippets.

**This needs a decision before Phase 1 proceeds on the current SRS/DESIGN wording.** FR-2, FR-4, ADR-002, and the architecture diagram in DESIGN-001 describe a service shape that doesn't exist in the real codebase. Flagged to David for a call: revise SRS-001/DESIGN-001/ADR-002 to describe hardening `ContainerRunner` + `WorkerResult` directly, or keep the original "new execution API" framing and treat this as a from-scratch addition that Orchid's orchestrator would call as one option among its existing isolation strategies. Not resolved yet — no doc changes made based on this finding until decided.

### Still open (Phase 0 checklist)

- [x] `runsc` install and version pin — `release-20260803.0` (see above)
- [x] Confirm `runsc` compatible with kernel `6.19.0-061900rc8-generic` — confirmed empirically via successful `--runtime=runsc` run
- [x] Audit Orchid `TesterAgent` current modes and task/result schema shape — see finding above; **reveals FR-2/FR-4/ADR-002/DESIGN-001 architecture need revision**
- [ ] Confirm Traefik config location for later allowlist wiring — candidates found: `/home/dave/LocalAI/orchid/scripts/traefik-orchid.yml` (Orchid-specific) vs. `/etc/traefik/traefik.yml` (host-wide, systemd-managed) — not yet confirmed which one governs egress for sandboxed containers
- [ ] Supported `language` values + base image(s) for the execution API — **superseded by the finding above**: `ContainerRunner` uses one fixed image (`python:3.12-slim`) running Orchid's own worker module, not user-selected-language snippets; revisit once the FR-2/ADR-002 question is resolved
- [ ] Default `timeout_s` / `memory_mb` values — no `--memory` flag exists on the current `docker run` call at all; this is now a real gap to fill, not just a default to pick
- [ ] Sandbox container teardown/cleanup step — current `ContainerRunner` already uses `--rm`, so containers self-clean on exit; still need to verify no orphans on timeout-kill path
- [x] `runsc` rollback plan — documented above (untested)
