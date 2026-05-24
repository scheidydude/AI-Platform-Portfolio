# ADR-004 — State Persistence Strategy

**Status:** `accepted`  
**Date:** 2026-05-23  
**Author:** David Scheiderman

---

## Context

`PipelineState` must be persisted after every state transition so the pipeline can resume from the last completed task without re-running earlier work (FR-07.3). Need to decide between disk-based JSON files and SQLite. Decision affects resume logic complexity, query-ability of state, and dependency footprint.

---

## Decision

**JSON to disk.** Write `PipelineState` as a single JSON file after every state transition. Use atomic write (write to `.tmp`, then `os.replace()`) to mitigate mid-write corruption risk.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| JSON to disk | Zero dependencies, human-readable, trivially inspectable during debugging, Pydantic serializes natively | No transactions; requires atomic write pattern to avoid corruption |
| SQLite | ACID transactions, survives mid-write crash, query-able | More complex schema, ORM or raw SQL needed, harder to inspect by eye |
| Redis | Fast, native pub/sub for streaming future | External dependency, overkill for PoC |

---

## Rationale

JSON is chosen for simplicity and debuggability. Since `PipelineState` is a single Pydantic model, `model.model_dump_json()` is all that's needed to persist. Human-readable state files are valuable during Phase 5 failure experiments — being able to open the state file and see exactly where the pipeline was is a significant debugging advantage. The corruption risk is mitigated by the atomic write pattern: write to `pipeline_<id>.tmp.json`, then `os.replace()` to the final path (POSIX atomic on same filesystem).

---

## Consequences

**Positive:**
- Zero added dependencies
- State files human-readable — critical for Phase 5 experiment debugging
- Pydantic `.model_dump_json()` / `.model_validate_json()` round-trip is trivial
- Atomic write pattern makes corruption unlikely in practice

**Negative / trade-offs:**
- No query-ability — must load entire state to inspect any field
- Not suitable for high-frequency writes (not a concern at this scale)

**Risks:**
- Phase 5 experiment #4 (mid-run kill) will stress-test the atomic write pattern — expected finding is that the `.tmp` file may be left on disk, requiring cleanup on resume

---

## Related ADRs

- ADR-005: Orchestration pattern

---

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-05-23 | `proposed` | Options framed, decision pending |
| 2026-05-23 | `accepted` | JSON to disk with atomic write pattern |
