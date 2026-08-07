# ADR-001 — Reuse P07's Execution API Contract Verbatim

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

P08 needs an execution API for submitting code to a Firecracker microVM and getting back a bounded result. [Project 07](../../../project-07-gvisor-sandbox/) already defines one for its gVisor backend: `{code, timeout_s, memory_mb, network}` → `{stdout, stderr, exit_code}`.

## Decision

P08 implements the identical request/response contract defined by P07, rather than designing a new one. No field is added, removed, or renamed without updating both projects' SRS documents.

## Rationale

- The stated goal of P08 is to be an interchangeable backend from Orchid's perspective — that claim is only true if the contract is actually identical, not merely similar.
- A shared contract means a single test harness can validate both backends (P07 SRS FR-2, P08 SRS FR-2), which is itself part of the portfolio evidence.
- Designing a second contract would fork the two projects' integration surface with Orchid for no functional benefit.

## Consequences

- P08 is constrained to whatever P07 finalizes at its Phase 2. If P07's contract needs to change after P08 has started, that change must be renegotiated in both projects' documentation, not just P08's.
- P08's `language` field (present in P07's request shape) may be a no-op or fixed value if the Firecracker rootfs only supports one execution environment — this is a documented simplification, not a contract deviation.
