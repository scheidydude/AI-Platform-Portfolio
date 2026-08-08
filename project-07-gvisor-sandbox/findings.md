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

## 2026-08-07 — Phase 1: syscall-interception test (FR-1 acceptance criterion met)

Two independent tests, both run via `scripts/verify_isolation.sh` (also runnable standalone; requires the invoking shell to have active `docker` group membership, e.g. via `sg docker -c ...`):

**Test 1 — kernel identity divergence.** `uname -a` / `cat /proc/version` under `--runtime=runc` return the real host kernel; under `--runtime=runsc` they return a fabricated identity. This proves the `uname`/`utsname` syscall is answered by the gVisor sentry itself, not passed through to the host kernel.

```
### runc (default runtime) ###
Linux b7a7ba1a18b9 6.19.0-061900rc8-generic #202602012244 SMP PREEMPT_DYNAMIC ... x86_64 GNU/Linux

### runsc (gVisor) ###
Linux 8e2217cc4bfc 4.19.0-gvisor #1 SMP Sun Jan 10 15:06:54 PST 2016 x86_64 GNU/Linux
```

**Test 2 — a syscall gVisor doesn't implement at all.** `io_uring_setup(2)` (syscall 425), called directly via `ctypes` in `scripts/probe_io_uring.py`. Three variants isolate exactly where each runtime intercepts:

```
### runc, Docker default seccomp ###
io_uring_setup() -> ret=-1 errno=1 (Operation not permitted)
# Docker's own seccomp profile blocks io_uring_setup here — not yet a kernel-level answer.

### runc, seccomp unconfined (raw host kernel behavior) ###
io_uring_setup() -> ret=3 errno=0 (none)
# Real host kernel (6.19 RC) genuinely implements io_uring_setup and succeeds — fd 3 returned.

### runsc (gVisor sentry) ###
io_uring_setup() -> ret=-1 errno=38 (Function not implemented)
# gVisor's sentry has no implementation of this syscall at all, regardless of seccomp policy —
# this is the sentry's own syscall table, not a filter sitting in front of the real kernel.
```

**Conclusion:** with seccomp taken out of the picture, the host kernel supports `io_uring_setup`; gVisor's sentry does not implement it and answers `ENOSYS` unconditionally. Combined with the kernel-identity divergence in Test 1, this is documented, reproducible evidence that `runsc` intercepts and independently answers guest syscalls rather than passing them through to the host kernel — satisfies FR-1's syscall-interception acceptance criterion.

**Artifacts:** `scripts/probe_io_uring.py`, `scripts/verify_isolation.sh` (both committed to the repo, re-runnable).

## 2026-08-07 — Phase 2: hardened `ContainerRunner` (FR-2, FR-4)

Changes made in the Orchid repo (`/home/dave/LocalAI/orchid`, separate git repo from this portfolio — not yet committed there, pending a branch/commit decision with David):

- `orchid/orchid.defaults.yaml`: added `isolation.container_runtime` (`""` default), `isolation.container_memory_mb` (`0` default), `isolation.container_cpus` (`0` default) — all default to current behavior (unset/no limit).
- `orchid/container_runner.py`: new `_build_docker_command()` builds the `docker run` argv from these config keys, adding `--runtime`, `--memory`, `--cpus` only when set. `run_task_isolated()` now also: drains `stderr` on a background thread (avoids a latent pipe-deadlock risk that existed before — stderr was never read at all), reaps the process after a timeout-kill (was previously left as a zombie), and populates `WorkerResult.exit_code`/`stdout`/`stderr` from the real container-level subprocess on every return path, including the existing "Worker exited without result" fallback.
- `orchid/worker_protocol.py`: `WorkerResult` gains `stdout: str = ""`, `stderr: str = ""`, `exit_code: int | None = None` — additive, defaults preserve every existing caller. `TaskContext`/`WorkerResult` JSON round-trip via `asdict`/`cls(**data)` is inherently backward/forward compatible with new optional fields.

**Verification:**
- Unit tests added: `tests/test_container_runner.py` (`_build_docker_command` with/without config; additive fields default correctly on the no-Docker path), `tests/test_worker_protocol.py` (`WorkerResult` new-field defaults). All pass.
- Full existing test file for both modules re-run clean (10/10). Broader `-k "orchestrator or worker or dispatcher or remote"` subset: 42 passed, 1 failed (`test_orchestrator_trace_log_written_on_task`) — confirmed **pre-existing and unrelated**: fails the same way with my changes stashed out, passes in isolation both with and without my changes. Order-dependent test pollution in the existing suite (an `AttributeError: 'MCPTool' object has no attribute 'server_name'` inside `orchestrator.py`, code I didn't touch), not a regression. Full suite run (`pytest tests/ -q`, ~1800 tests) kicked off to confirm at full scope — result pending as of this entry.
- Real Docker + `runsc` end-to-end (not mocked): `docker run --rm --runtime=runsc --memory=64m --cpus=1 python:3.12-slim python3 -c "print(...)"` runs clean (exit 0) — the exact flag shape `_build_docker_command()` produces is valid and accepted by Docker under `runsc`.
- Memory-ceiling enforcement (`scripts/probe_memory_limit.py`, committed): under `--runtime=runsc --memory=64m`, a script allocating up to 400MB is OOM-killed after ~100MB (`exit 137`); the identical script with no memory flag completes cleanly through the full 400MB (`exit 0`, prints `DONE`). This satisfies SRS-001 FR-2's memory-ceiling acceptance criterion — and flows through `ContainerRunner`'s existing generic "no result" fallback path with no special-casing needed: the container dies before emitting a `success` JSON line, so the pre-existing fallback returns `success=False`, and the new code attaches `exit_code=137` from the real `proc.returncode`.

**Not yet done (deferred to Phase 4 by design, per task_plan.md):** a live end-to-end run of `orchid.worker_subprocess`'s real ReAct agent loop (e.g. via `TesterAgent`) under `isolation.container_enabled` + `isolation.container_runtime: runsc`. That requires a reachable LLM inference endpoint and is explicitly Phase 4's acceptance criterion ("`TesterAgent` demo runs correctly under the hardened path"), not Phase 2's. Phase 2's own acceptance ("a known test task returns a correct `WorkerResult` ... with limits applied") is satisfied by the direct Docker-level proofs above, which exercise exactly the command `ContainerRunner` builds.

**Branch decision (resolved):** David chose a feature branch over direct-to-main. Created `p07-gvisor-hardening` off `main` in the Orchid repo.

**Full-suite run — aborted, not a regression.** Kicked off `pytest tests/ -q` (~1800 tests) in the background to double-check beyond the targeted subset. After ~35 minutes it had not finished and was still spawning new processes: real MCP server subprocesses (`npm exec @modelcontextprotocol/server-github`, `npm exec resend-mcp`, `orchid-mcp-smtp`) get started per-test and are never torn down, accumulating (30+ live children under the pytest process tree, still climbing). The host's swap was at 7.6/8.0 GB used at the time — killing the run barely moved it (7.4/8.0 GB after), meaning that pressure is pre-existing/ongoing on this shared homelab box (also running LLM inference and other live services), not caused by this test run or by my Phase 2 changes. Also found ~10 unrelated defunct/zombie `npm exec` processes dated **May27** (weeks old, from some earlier stuck run) — pre-existing, unrelated, harmless (zombies hold no memory), left alone.

**Decision: do not rely on the full suite for Phase 2 verification.** It's exercising a pre-existing, Orchid-wide test-hygiene bug (MCP subprocess leak across the suite), not something P07 should fix or wait on. Phase 2's acceptance rests on: the 10 targeted unit tests (pass), the 42/43 broader consumer-module subset (1 confirmed pre-existing unrelated flake, see above), and the real Docker+`runsc` end-to-end proofs (bounded-container run, memory-OOM kill). That's sufficient, documented evidence for FR-2/FR-4 without needing the full suite. Worth flagging to David separately, outside P07 scope: the MCP-subprocess-leak issue in Orchid's test suite is a real finding on its own.

**Committed:** Phase 2 changes committed to `p07-gvisor-hardening` (not merged to `main` — that's a separate decision for David, not part of this P07 task).

## 2026-08-07 — Traefik config resolved: neither candidate governs egress (another wrong assumption)

Resolved the last open Phase 0 checklist item. Checked both candidates plus the live systemd Traefik service directly:

- `systemctl status traefik` confirms the one real, running instance loads `/etc/traefik/traefik.yml` (`ExecStart=... --configFile=/etc/traefik/traefik.yml`), active since 2026-07-02.
- That static config's only provider is `file: {directory: /etc/traefik/dynamic, watch: true}` — a **dynamic config directory**, checked directly: `services.yml` and `salli.yml`, both containing only `http.routers`/`http.services` entries with `Host()` rules proxying external HTTPS traffic to local backends (`llama`, `comfy`, `tts`, `orchid` → `127.0.0.1:7842`, `salli` → `127.0.0.1:8010`). No `forwardAuth`, no egress/forward-proxy config anywhere.
- Orchid's own `scripts/traefik-orchid.yml` is an ingress-routing **template** for exactly the same pattern (routes `orchid.your-domain.com` → `localhost:7842`) — a distributable example, not what's actually deployed. The real live route for Orchid is in `/etc/traefik/dynamic/services.yml`, using the real domain `orchid.scheidy.com`.
- No forward-proxy tooling installed on the host at all (checked `squid`/`tinyproxy`/`privoxy` — none present). No custom Docker networks either — just the three defaults (`bridge`, `host`, `none`).

**Conclusion: Traefik on this host is ingress-only** (external HTTPS → internal service). It has no role in, and no mechanism for, controlling a sandboxed container's *outbound* traffic. SRS-001 FR-3 / DESIGN-001 / `task_plan.md` Phase 3's premise — "allowlist mode routes through the existing Traefik/proxy configuration" — is wrong, the same way the original `TesterAgent`-mode assumption was in Phase 0. This is the second design assumption that didn't survive contact with the real host.

**What this means for Phase 3:** default-deny itself needs no new infrastructure — `--network none` on the `docker run` command (already how `_build_docker_command()` is structured to grow) is sufficient and Docker-native. The **allowlist** half genuinely has nothing to build on — it would be new infrastructure, not hardening of something existing (unlike Phase 2). Options worth considering: (a) a small dedicated forward-proxy container (e.g. `tinyproxy`/`squid` with an ACL) that an allowlisted sandbox is pointed at via `HTTP_PROXY`/`HTTPS_PROXY`, with the sandbox's own network still `none` or restricted to a private bridge that can only reach the proxy; (b) a custom Docker bridge network + `iptables`/`nftables` DNAT/allow rules keyed to destination IP (fragile for domain-based allowlisting, since IPs change); (c) DNS-based filtering (e.g. a custom `--dns` pointed at a resolver that only resolves allowlisted domains, paired with egress IP restriction so raw-IP bypass isn't possible). Not decided yet — flagged to David before starting Phase 3 implementation.

## 2026-08-07 — Phase 3: Squid egress-allowlist sidecar implemented (FR-3, ADR-004)

David chose the forward-proxy sidecar (option (a) above), over DNS-filtering and iptables/nftables. Recorded as ADR-004. Implemented in the Orchid repo, on the `p07-gvisor-hardening` branch:

- `orchid/sandbox_egress.py` (new module): manages a Squid sidecar container (`ubuntu/squid:latest`) dual-homed onto an `--internal` Docker network (`orchid-sandbox-internal`, no outside route) plus the normal default bridge (external access). `ensure_egress_proxy(domains)` is idempotent — creates the network/container on first call, hot-reconfigures Squid (`squid -k reconfigure`, falling back to a restart if that fails) on subsequent calls with a changed allowlist. Config template: `orchid/sandbox_egress_squid.conf.template` (standard `Safe_ports`/`SSL_ports`/`CONNECT` ACLs plus a `dstdomain` allowlist read from a separately mounted file, so the allowlist can change without touching the Squid config itself).
- `orchid/orchid.defaults.yaml`: added `isolation.container_egress_allowlist` (default `[]`).
- `orchid/container_runner.py`: `_build_docker_command()` now always sets `--network` — `none` by default (FR-3's actual default-deny; previously **no** `--network` flag was set at all, meaning the default Docker bridge with full internet access. This is a deliberate behavior change per spec, not a bug — flagged clearly in the commit), or the internal network + `HTTP_PROXY`/`HTTPS_PROXY` env vars when `isolation.container_egress_allowlist` is non-empty.
- Unit tests: `tests/test_sandbox_egress.py` (new, 5 tests) + additions to `tests/test_container_runner.py` (2 tests: default `--network none`, allowlist wiring). All pass, plus the full existing `test_container_runner.py`/`test_worker_protocol.py` suites (16/16) and the broader 52-test consumer-module regression subset (clean, run with `--ignore=tests/test_trace.py` to skip the already-documented pre-existing flaky test).

**Real end-to-end verification** (not just mocked) — five separate live tests against the actual sidecar:
1. `--network none`: DNS resolution itself fails (`[Errno -3] Temporary failure in name resolution`) — no network stack at all.
2. Allowlisted domain (`example.com`) via the proxy, HTTP: `SUCCESS 200`.
3. Non-allowlisted domain (`wikipedia.org`) via the same proxy, HTTP: `HTTP Error 403: Forbidden` — Squid's ACL denies it.
4. Same allowlisted/non-allowlisted pair over HTTPS (CONNECT tunnel): allowlisted succeeds (`SUCCESS 200`), non-allowlisted fails at the tunnel step (`Tunnel connection failed: 403 Forbidden`) — confirms the ACL applies to the CONNECT target (SNI-equivalent), not just plaintext HTTP, so Squid never needs to MITM/decrypt TLS.
5. All four cases re-run under `--runtime=runsc` composed with the Phase 2 hardening — same results, confirming Phase 2 and Phase 3 hardening compose correctly.

**Real finding, not a bug: gVisor can't resolve Docker's embedded DNS on a user-defined network.** First attempt at test 5 used the proxy's *container name* (as under `runc`, which worked fine) and failed under `--runtime=runsc` with the same `[Errno -3] Temporary failure in name resolution` — but this time for the proxy's own hostname, on a network path that otherwise worked. Isolated by testing the identical lookup under `runc` (works) vs. `runsc` (fails), then confirming raw-IP addressing works under both. Conclusion: gVisor's netstack does not properly resolve names via Docker's embedded DNS server (127.0.0.11) on a custom bridge network — a real, documented gVisor limitation, not a bug in this code. **Fix:** `sandbox_egress.ensure_egress_proxy()` now returns `http://<proxy-IP>:3128` (looked up via `docker inspect`) rather than `http://<container-name>:3128`, sidestepping the DNS path entirely. This is exactly the kind of "what gVisor doesn't solve" material DESIGN-001's deliverables ask for — goes directly into the gVisor-vs-Firecracker comparison write-up.

**Committed** to `p07-gvisor-hardening` in the Orchid repo (not merged to `main`, David's call, consistent with the Phase 2 branch decision).

## 2026-08-07 — Phase 4: consumer regression check + real live end-to-end demo

### Consumer regression check (FR-4, first half)

Ran every test file touching `orchestrator.py`, `remote/worker_server.py`, `remote/dispatcher.py`, or `worker_subprocess.py` individually (not the full leaky suite — see the earlier MCP-leak entry): `test_integration.py`, `test_tester_agent.py`, `test_multi.py`, `test_metrics.py`, `test_providers.py`, `test_routing.py`, `test_trace.py`, `test_rollup.py`, `test_remote_dispatcher.py`. Result: 8 failures across 3 files (`test_metrics.py` ×2, `test_providers.py` ×6, `test_rollup.py` ×1) — every one confirmed **identical on `main`** (checked out `main`, re-ran each failing file, same failures, same error messages: the `MCPTool.server_name` `AttributeError` and unrelated provider-routing assertion mismatches). Zero regressions from any P07 work. `test_integration.py`/`test_metrics.py`/`test_trace.py` also showed order-dependent pollution when run *together* (matches the pattern already documented for `test_trace.py` alone) — all pass individually.

### Real live demo (FR-4, second half) — and three more pre-existing bugs found along the way

Set out to run a real `TesterAgent` task through `ContainerRunner.run_task_isolated()` under `isolation.container_runtime: runsc`, per Phase 4's acceptance criterion. Hit three genuine, pre-existing bugs — none related to gVisor, none introduced by P07 — that meant `isolation.container_enabled=true` had **never actually worked, for any task, ever**:

1. **`_prepare_project` read `ctx.project_path`, a field that doesn't exist on `TaskContext`** (the real field is `project_dir`). This alone would `AttributeError` on the very first call, before Docker even runs.
2. **`_prepare_project` used `shutil.copytree` unconditionally on every top-level item** in the project directory — crashes with `NotADirectoryError` on any top-level *file* (i.e. almost every real project: `README.md`, `pyproject.toml`, anything not a directory).
3. **No volume mounts at all.** `docker run ... {image} {sys.executable} -m orchid.worker_subprocess` referenced `sys.executable` — correctly, that's the host's own `.venv` interpreter path (e.g. `/home/dave/LocalAI/orchid/.venv/bin/python3`) — but nothing ever mounted that path, the `orchid` package, or the target project into the container. Confirmed directly: `docker run --rm python:3.12-slim python3 -m orchid.worker_subprocess` → `ModuleNotFoundError: No module named 'orchid'`.

**Fixes**, all in `orchid/container_runner.py`:
- `ctx.project_dir` (not `project_path`) in `_prepare_project`.
- File-vs-directory branch in `_prepare_project`'s copy loop (`shutil.copy2` for files, `shutil.copytree` for directories).
- `_build_docker_command(project_dir)` now takes the prepared project dir and mounts it at `WORKDIR`, plus mounts `ContainerRunner.ORCHID_ROOT` (computed dynamically, read-only) so the container can import `orchid` via the exact same editable install the host uses. Also added `_venv_extra_mount_dirs()`: `sys.executable` on this host resolves through a **uv-managed standalone Python toolchain** living outside the repo (`~/.local/share/uv/...`, itself several layers of symlinks — `pyvenv.cfg`'s `home` field points at yet another alias directory, so a narrowly-scoped mount of just the final resolved path wasn't sufficient; mounting the whole `~/.local/share/uv` cache read-only was the robust fix). This only activates when the interpreter actually lives outside `ORCHID_ROOT` — a plain system-Python venv wouldn't need it.

**Verified the fix directly** (not through the full agent loop yet): `docker run --rm -v /home/dave/LocalAI/orchid:/home/dave/LocalAI/orchid:ro -v <uv-toolchain>:<uv-toolchain>:ro ... /home/dave/LocalAI/orchid/.venv/bin/python3 -c 'from orchid.orchestrator import _get_registry; print(_get_registry().keys())'` → succeeds, lists all agent types including `tester`.

**Fourth gap, found running the actual demo:** the container gets zero host environment variables by default (by design, to avoid leaking secrets) — but that also means `LLAMA_BASE_URL` never reaches the agent, so *any* LLM call fails inside a fully isolated task, including `TesterAgent`'s own ReAct loop (the whole agent run, LLM calls included, executes inside the container in this architecture — not just tool/code execution). Added `isolation.container_env` (default `{}`): an explicit, opt-in dict of env vars forwarded into the container, deliberately narrow rather than a blanket host-environment passthrough — consistent with the project's "explicit allowlist over implicit access" theme (same spirit as FR-3's domain allowlist).

**Fifth gap:** Squid's `Safe_ports` ACL only allowed 80/443 — denied the LAN LLM endpoint's port (8082) before the domain allowlist was ever checked. Added `acl Safe_ports port 8081-8082` (the two local LLM/embedding ports used on this homelab) to `sandbox_egress_squid.conf.template`.

**Full live demo, all fixes applied together:**
```python
c = cfg.get_config()
c["isolation"]["container_runtime"] = "runsc"
c["isolation"]["container_memory_mb"] = 512
c["isolation"]["container_egress_allowlist"] = ["ai.scheidy.com"]
c["isolation"]["container_env"] = {"LLAMA_BASE_URL": "http://ai.scheidy.com:8082/v1"}

ctx = TaskContext(agent_type="tester", task_description="Run the test suite...", ...)
result = ContainerRunner().run_task_isolated(ctx, timeout_s=120)
```
Result: `success=True`, `exit_code=0`, `duration_s=54.08` (real 35B-model inference time), `result={"passed": true, "tests_run": 1, "failures": [], "files_checked": ["test_trivial.py"]}` — a genuine, live, end-to-end `TesterAgent` run: real LLM calls, real ReAct loop, real pytest execution, under `runsc`, under a 512MB memory cap, with network locked to exactly one allowlisted LAN domain. No orphaned containers afterward (`docker ps -a` shows only the long-running Squid sidecar).

**Unit tests:** added `test_build_docker_command_mounts_project_and_orchid_root` and `test_prepare_project_uses_project_dir_field` (regression test for bug #1/#2) to `test_container_runner.py`; updated the three existing `_build_docker_command()` call sites for its new `project_dir` parameter. Full P07 test set: 18/18. Broader regression set (8 files covering all four `WorkerResult` consumers plus P07's own tests): 86/86 passing.

**Reflection:** this is the clearest example in the whole project of why the recon-first, verify-live approach mattered — `isolation.container_enabled` looked like existing, working infrastructure to harden (that was the whole premise of the Phase 0 pivot), but it had never actually been exercised end-to-end. Hardening a mechanism and *making that mechanism real* turned out to be the same piece of work here. Worth stating plainly in the portfolio write-up rather than implying `ContainerRunner` was already solid before P07 touched it.

**Committed** to `p07-gvisor-hardening` in the Orchid repo (not merged to `main`, consistent with prior phases).
