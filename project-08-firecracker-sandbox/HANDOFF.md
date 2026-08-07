# P08 Handoff — Firecracker MicroVM Execution Backend

**Current state:** Scoped and scaffolded. No implementation started.

**Where this runs:** NucBox EVO X2 (Linux, AMD host with ROCm drivers, KVM required). This repo needs to be cloned onto that host and run via Claude Code CLI there — Firecracker requires KVM and does not run on macOS.

**Sequencing:** Do not start before [Project 07 — gVisor Sandbox](../project-07-gvisor-sandbox/) has at least a finalized execution API contract (Phase 2 of P07). This project reuses that contract rather than designing a new one.

**Exact next action:** Phase 0/1 — confirm KVM is available and enabled on the NucBox, confirm Firecracker compatibility with the host kernel alongside existing ROCm drivers, then build a stripped kernel + Alpine rootfs and measure cold boot. See `task_plan.md` Phase 1 and `docs/design/DESIGN-001.md` §3. Full document set indexed in `INDEX.md`.

**Known risk area (from design doc, unverified):** Phases 4/5 (snapshot/restore) are flagged as highest-risk on this specific hardware — AMD host, ROCm drivers potentially interacting with KVM/Firecracker. Budget debugging time here and document any host-specific quirks; that friction is itself portfolio signal, don't hide it.

**Gotchas to expect:**
- Keep VM pool size small for the demo (2–3 warm VMs) — this is a portfolio proof, not a load test.
- Final deliverable must include a comparison doc against the P07 gVisor backend, not two standalone writeups.
