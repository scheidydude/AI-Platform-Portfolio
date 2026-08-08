# P08 Handoff — Firecracker MicroVM Execution Backend

**Current state:** Scoped and scaffolded. No implementation started. [Project 07 — gVisor Sandbox](../project-07-gvisor-sandbox/) is now fully complete through its core phases (1–5) — this project's sequencing dependency is satisfied. Read this whole file before starting, not just the next action — several things below correct or update the original design docs.

**Where this runs:** NucBox EVO X2 (Linux, AMD host with ROCm drivers, KVM required). Claude Code sessions in this repo run directly on that host — confirmed during P07's work; does not run on macOS.

**KVM already confirmed available** (found during P07 Phase 0 recon, 2026-08-07): `/dev/kvm` present, `kvm_amd`/`kvm` kernel modules loaded — no separate KVM enablement work needed. See [P07's findings.md](../project-07-gvisor-sandbox/findings.md).

**Execution contract — read before Phase 2:** this project's docs (SRS-001 FR-2, DESIGN-001) still describe reusing a `{code, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code}` contract from P07. That contract never actually existed — P07's own Phase 0 recon found it was a wrong assumption about Orchid's real codebase (see [P07's findings.md](../project-07-gvisor-sandbox/findings.md) and its ADR-002). **The real, now-hardened contract is Orchid's `WorkerResult` dataclass** (`orchid/worker_protocol.py`): `task_id, success, result, error, duration_s, cpu_seconds`, plus P07's additive `stdout`, `stderr`, `exit_code`, `syscall_log_path` fields. Update SRS-001/DESIGN-001 to reflect this before implementing Phase 2 (execution API parity) — reuse `WorkerResult` additively, the same pattern P07 used throughout, don't reintroduce the old imagined shape.

**Exact next action:** Phase 0/1 — confirm Firecracker compatibility with the host kernel (`6.19.0-061900rc8-generic`, a mainline RC build — P07 also had to re-verify `runsc` against this specific kernel rather than assuming generic distro compatibility) alongside existing ROCm drivers, then build a stripped kernel + Alpine rootfs and measure cold boot. See `task_plan.md` Phase 1 and `docs/design/DESIGN-001.md` §3. Full document set indexed in `INDEX.md`.

**Known risk area (from design doc, unverified):** Phases 4/5 (snapshot/restore) are flagged as highest-risk on this specific hardware — AMD host, ROCm drivers potentially interacting with KVM/Firecracker. Budget debugging time here and document any host-specific quirks; that friction is itself portfolio signal, don't hide it.

**Gotchas to expect:**
- Keep VM pool size small for the demo (2–3 warm VMs) — this is a portfolio proof, not a load test.
- Final deliverable must include a comparison doc against the P07 gVisor backend, not two standalone writeups. **A first draft already exists, written from P07's side:** [`COMPARISON-001-gvisor-vs-firecracker.md`](../project-07-gvisor-sandbox/docs/comparison/COMPARISON-001-gvisor-vs-firecracker.md) — covers what P07 proved, gVisor's real empirical limitations, and an architecture-level (not yet measured) view of what Firecracker adds. Revise it with real numbers once this project has cold-start/pool-latency/snapshot-restore data, rather than writing a second, separate comparison.
- Claude Code has no `sudo` on the NucBox — hand off privileged steps (installs, KVM/Firecracker permission setup) for David to run manually, same as P07's `runsc` install.
- Orchid's full test suite (`pytest tests/ -q`, ~1800 tests) has a pre-existing, unrelated bug: it leaks real MCP server subprocesses and can run indefinitely. Use targeted test files/`-k` filters instead of the full suite (see P07's findings.md for detail).
