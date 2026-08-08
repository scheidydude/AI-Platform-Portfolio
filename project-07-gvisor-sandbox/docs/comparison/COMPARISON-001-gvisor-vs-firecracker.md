# COMPARISON-001 — gVisor vs. Firecracker: Isolation Strategy for Orchid

**Version:** 1.0
**Date:** 2026-08-07
**Author:** David Scheiderman
**Status:** Draft — P07 (gVisor) complete through Phase 5; [Project 08](../../../project-08-firecracker-sandbox/) (Firecracker) not yet implemented
**Project:** Project 07 — Sandboxed Tool Execution (gVisor)

Requested by [DESIGN-001](../design/DESIGN-001.md)'s Phase 4 deliverables: "why gVisor here, what it doesn't solve, what Firecracker adds." Written from P07's side, since P07 is sequenced first and P08 reuses its execution contract (see §5).

---

## 1. Two different isolation primitives

**gVisor (`runsc`)** is an application-level sandbox. A user-space process (the "sentry") intercepts every syscall a container makes — via ptrace or, on this host, the faster `systrap` platform (confirmed in `runsc`'s own boot log: `Platform: systrap`) — and answers it itself instead of passing it to the real Linux kernel. The container still runs on the host kernel's process/network/cgroup infrastructure; what changes is that the *syscall surface* the container sees is gVisor's reimplementation, not the host's.

**Firecracker** is a hardware-virtualized microVM. Each sandboxed workload gets its own guest kernel running under KVM, with a minimal virtual machine monitor exposing only ~5 emulated devices. The isolation boundary is the same one a full VM gets — a separate kernel, separate address space, hypervisor-mediated hardware access — just with a boot path stripped down to reach usable state in tens of milliseconds instead of seconds.

The practical difference: gVisor's boundary is "the syscalls the sentry chooses to implement, running on the same physical kernel as everything else on the host." Firecracker's boundary is "a different kernel, full stop." Neither is strictly "more secure" in the abstract — they trade different things.

## 2. What P07 actually built and proved

Everything below is measured, not asserted — see `findings.md` for full commands and output.

| Capability | Evidence |
|---|---|
| Syscall interception is real | `uname`/`/proc/version` return a fabricated `4.19.0-gvisor` kernel under `runsc`, the real host kernel under `runc`. `io_uring_setup` succeeds on the raw host kernel (seccomp disabled) but returns `ENOSYS` unconditionally under `runsc` — gVisor's own syscall table simply doesn't implement it |
| Resource ceilings enforced | A memory-bomb script is OOM-killed (`exit 137`) under a 64MB cap under `runsc`, completes cleanly unconstrained |
| Network policy enforced | Default `--network none` fails DNS resolution entirely; an allowlisted domain succeeds over HTTP and HTTPS through a Squid sidecar; a non-allowlisted domain gets a 403 from Squid's ACL, on both protocols, under both `runc` and `runsc` |
| Real workload runs correctly | A live `TesterAgent` task — real LLM call, real ReAct loop, real `pytest` execution — completed successfully under `runsc` + a 512MB memory cap + a one-domain network allowlist |
| Per-execution observability | Real syscall traces captured and retrievable by task ID (e.g. a live run: 8,309 syscalls, top offenders `stat`/`read`/`fstat`/`lseek`/`openat` — a plausible profile for a Python-import-heavy container boot) |

## 3. What gVisor doesn't solve — found empirically, not theorized

Two genuine limitations surfaced during this project, both documented in `findings.md` in full:

**gVisor's netstack can't resolve Docker's embedded DNS on a user-defined bridge network.** A container under `runsc` failed to resolve another container's name by DNS, with the identical lookup succeeding under `runc`. Root cause: gVisor reimplements the network stack too, and its DNS resolution path doesn't correctly reach Docker's embedded resolver (127.0.0.11) the way the host kernel's does. Worked around with IP-based addressing, but it's a real, class-of-bug limitation of syscall/network reimplementation: gVisor doesn't just need to intercept syscalls correctly, it needs to *behave identically* to the real kernel across every code path a workload might exercise, and coverage gaps like this are the direct cost of that reimplementation strategy.

**Whole-task isolation puts the agent's own LLM calls inside the sandbox boundary.** Orchid's `ContainerRunner` isolates an entire agent task — including the agent's own reasoning loop, which calls out to an LLM inference endpoint to decide what to do next. That means a fully locked-down sandbox (`--network none`) also cuts off the agent's ability to function at all; getting a real end-to-end demo working required an explicit, narrow network allowlist and env-var passthrough (`isolation.container_env`) just to let the agent reach its own model server. This isn't a gVisor limitation specifically — it's an architectural consequence of isolating "the task" rather than "the tool/code execution within the task" — but it's a real friction point this project's design didn't originally account for (see `findings.md`'s Phase 4 entry), and it shapes what "sandboxing" can mean for an agentic system: the isolation boundary and the LLM-reachability requirement are in tension by construction, not by bug.

**What gVisor does *not* attempt to solve, by design:** kernel-level exploits that don't rely on an unimplemented or buggy syscall path succeed exactly as well against gVisor's sentry as against the host kernel it's written in, because the sentry itself is a large, privileged Go program parsing untrusted input (guest syscalls). gVisor narrows the attack surface (a container can't reach real kernel code paths directly) but doesn't eliminate "escape the sandbox into the host" as a threat category the way a hardware-enforced VM boundary does.

## 4. What Firecracker would add (P08, not yet built)

This section is architecture, not measurement — P08 hasn't started. Flagged explicitly per this portfolio's own honesty standard (see P08's ADR-003: report real numbers, don't chase idealized ones).

- **A materially stronger isolation boundary.** A Firecracker guest has its own kernel; an exploit in the guest kernel doesn't hand an attacker host kernel code execution the way a sentry compromise theoretically could. This directly addresses gVisor's residual risk described above (§3, last paragraph).
- **Snapshot/restore of full VM state.** This is the capability gVisor's container-per-task model doesn't have an equivalent for: pausing a running microVM, persisting its memory and device state to disk, and resuming it — possibly on a different host process — after a simulated failure. P08's whole reason for existing (per its own DESIGN-001) is to demonstrate exactly this for long-running agent tasks, which is a different capability axis than isolation strength: it's about *durable execution across failure*, not about *what the sandbox can prevent*.
- **Cold-start and pool-latency tradeoffs — real numbers TBD.** Firecracker's own published benchmarks claim ~125ms cold boots; P08's SRS explicitly commits to reporting whatever this homelab's AMD/ROCm hardware actually produces, target or not (P08 ADR-003). Until that data exists, any specific number here would be exactly the kind of unverified claim this whole project has been correcting one Phase at a time — so it's deliberately not asserted.
- **More moving parts.** P08's own design already reflects this: a VM pool manager to amortize cold-start (P08 FR-3), a snapshot store, and a restore path — meaningfully more infrastructure than gVisor's "add a runtime flag to `docker run`" integration surface. Operational complexity is a real cost, not just an isolation-strength dial.

## 5. A contract note for P08

P07's original design assumed a `{code, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code}` execution contract that P08 was meant to reuse. Phase 0 recon found that contract didn't match Orchid's real codebase (see `findings.md` and ADR-002) — the actual, now-hardened contract is Orchid's `WorkerResult` dataclass (`task_id, success, result, error, duration_s, cpu_seconds`, plus P07's additive `stdout`/`stderr`/`exit_code`/`syscall_log_path` fields). **P08's docs still reference the original, superseded contract** and will need updating to consume `WorkerResult` before P08's Phase 2 (execution API parity) can be meaningfully implemented — noted here so it isn't rediscovered from scratch.

## 6. Decision framework

| If the requirement is... | Reach for... |
|---|---|
| Fast, low-overhead isolation for many short-lived tasks, with fine-grained syscall/network policy | gVisor — proven in this project: sub-second overhead, no extra pool/VM management, direct Docker integration |
| Surviving a host failure or deploy mid-task, or explicitly demonstrating checkpoint/resume | Firecracker — this is a capability gVisor's model doesn't have an answer for, not just a "more secure" alternative |
| Defense against a genuinely adversarial, untrusted-code-execution threat model (not just "don't let an agent's own tool calls misbehave") | Firecracker's hardware-enforced boundary is the more defensible security story; gVisor's is "meaningfully narrower attack surface than nothing," not "equivalent to a real VM" |
| Minimizing new infrastructure and operational surface | gVisor — it is, concretely, a Docker runtime flag plus a sidecar proxy; Firecracker requires a pool manager and snapshot store by its own design |

Both are legitimate answers to different questions. P07 answers "how do I bound what a task can do." P08 is scoped to answer a question P07's architecture structurally cannot: "how do I survive this task's execution environment disappearing out from under it."

---

*Status: Draft. Will be revised with real P08 measurements (cold-start, pool latency, snapshot/restore proof) once that project reaches its own Phase 1–5.*
