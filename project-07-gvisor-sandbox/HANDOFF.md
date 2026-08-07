# P07 Handoff — gVisor Sandboxed Execution

**Current state:** Scoped and scaffolded. No implementation started.

**Where this runs:** NucBox EVO X2 (Linux, existing Docker/Traefik stack). This repo needs to be cloned onto that host and run via Claude Code CLI there — `runsc` and cgroup-based isolation do not work on macOS.

**Exact next action:** Phase 0/1 — confirm the NucBox host kernel and Docker version support `runsc`, then install it as a secondary Docker runtime (`--runtime=runsc`) alongside the existing default-runtime containers. See `task_plan.md` Phase 1 acceptance criteria and `docs/design/DESIGN-001.md` §3. Full document set indexed in `INDEX.md`.

**Sequencing note:** This project should be completed (at minimum through Phase 4) before starting [Project 08 — Firecracker](../project-08-firecracker-sandbox/), which depends on this project's execution API request/response contract (`{code, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code}`).

**Gotchas to expect (from design doc, unverified):**
- Orchid's `TesterAgent` currently only supports `verify_syntax_only` — the new `sandboxed_execution` mode must be additive, not a replacement.
- Reuse Orchid's existing task/result schema; do not introduce a parallel result format.
- Execution API is host-local for v1 — no auth/multi-user exposure needed (portfolio demo, not production service).
