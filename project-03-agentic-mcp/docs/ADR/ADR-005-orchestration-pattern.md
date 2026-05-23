# ADR-005 — Orchestration Pattern

**Status:** `proposed`  
**Date:** 2026-05-23  
**Author:** David Scheiderman

---

## Context

Need to choose how the pipeline coordinates agents. Sequential (Planner → all Researcher tasks → Synthesizer) is simple to reason about and debug. Streaming (Researcher tasks feed Synthesizer incrementally) has better latency but significantly higher state complexity. Project spec recommends starting sequential and evaluating streaming explicitly.

---

## Decision

**Start with sequential orchestration. Evaluate streaming in Phase 4 and document whether its complexity is justified.**

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Sequential | Simple, easy to debug, straightforward resume logic | Higher latency (Synthesizer waits for all findings) |
| Streaming (incremental) | Lower perceived latency, Synthesizer can start early | Complex state management, harder resume logic |
| Parallel Researcher tasks (within sequential) | Reduces wall time without streaming complexity | Requires async coordination, more complex error propagation |

---

## Rationale

Sequential chosen first because:
1. Project goal is learning failure modes, not optimizing latency
2. Simpler resume logic satisfies FR-07.3 with less risk
3. Streaming can be evaluated in Phase 4 with documented trade-offs — the act of comparison is itself a deliverable

Whether to add parallel Researcher tasks (within sequential orchestration) is deferred to Phase 4 evaluation.

---

## Consequences

**Positive:**
- Easier to debug agent handoffs in Phase 2–3
- Resume logic is straightforward (replay from last completed `ResearchTask`)
- Failure mode experiments (Phase 5) are easier to set up

**Negative / trade-offs:**
- Synthesizer has higher latency (waits for all findings)
- Parallel researcher execution deferred

**Risks:**
- If streaming is needed for Orchid V3, this PoC won't demonstrate it directly — mitigated by Phase 4 evaluation doc

---

## Related ADRs

- ADR-001: Language and framework
- ADR-004: State persistence

---

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-05-23 | `proposed` | Sequential chosen, streaming evaluation deferred to Phase 4 |
