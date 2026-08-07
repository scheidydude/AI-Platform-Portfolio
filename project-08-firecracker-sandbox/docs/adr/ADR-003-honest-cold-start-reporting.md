# ADR-003 — Report Real Cold-Start Numbers Instead of Chasing a Target

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

Firecracker is commonly cited as achieving sub-200ms cold starts. The NucBox is an AMD host with ROCm drivers installed, running KVM/Firecracker in a configuration that hasn't been verified against that combination before this project starts. Actual cold-start numbers on this specific hardware are unknown going in.

## Decision

FR-1's acceptance criterion is "boot time under 200ms, **or** documented with an explanation if not." The project reports actual measured numbers on the real hardware, and explains any deviation, rather than tuning the demo or the hardware setup until a target number is hit.

## Rationale

- The source design doc explicitly deprioritizes target-chasing: real homelab hardware numbers are the point, not an idealized figure.
- An AMD host with ROCm drivers is an atypical Firecracker deployment target; if that combination introduces measurable overhead, that is itself a finding worth documenting for an interview conversation, not a result to hide.
- Phases 4/5 (snapshot/restore) are separately flagged as the highest-risk phases on this hardware ([SRS-001](../srs/SRS-001.md) NFR-4) — the same honesty principle applies there.

## Consequences

- A missed cold-start target is not treated as project failure; failing to document *why* it was missed would be.
- The final comparison doc against P07 must include real measured numbers for both backends, not representative/marketing figures from either technology's general reputation.
