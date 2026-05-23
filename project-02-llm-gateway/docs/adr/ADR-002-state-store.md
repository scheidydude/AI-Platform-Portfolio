# ADR-002 — State Store: SQLite → Redis

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

Quota counters and request logs need persistent storage. Two competing requirements:

1. **Simplicity** — POC should stand up without external infrastructure
2. **Correctness under concurrency** — quota enforcement requires atomic increment-and-check; two concurrent requests both passing a quota check at the limit is a real bug

---

## Decision

**SQLite for Phase 1. Redis upgrade path documented and wired in Phase 2.**

Not "use one or the other" — use SQLite to get moving, explicitly migrate to Redis when quota enforcement goes in.

---

## Rationale

### Why SQLite first

- Zero infrastructure: no daemon, no Docker, no connection pooling
- Python stdlib (`sqlite3`); no dependencies
- Sufficient for single-process POC with low concurrency
- Gets the data model proven before introducing infra complexity

### Why Redis later (not now)

Quota enforcement requires **atomic read-increment-check**. In Redis:

```
INCRBY team:cloud-engineering:tokens 1183
```

This is atomic. In SQLite under concurrent writes, two requests can both read `4,999,000 / 5,000,000` and both proceed, resulting in `5,001,183` — a quota bust. WAL mode + `BEGIN IMMEDIATE` mitigates this in SQLite but it's a workaround, not a solution.

Redis `INCRBY` is single-threaded and atomic by design. It's the right tool when multiple async workers share quota state.

### Why not Redis from day one

- Adds infra dependency for a POC
- Forces Docker or Redis install before any code runs
- SQLite is sufficient until Phase 2 enforcement modes are implemented
- The upgrade is a single module swap (`state/sqlite.py` → `state/redis.py`) behind a common interface

---

## Migration Path

State store abstracted behind interface:

```python
class QuotaStore:
    async def get_usage(self, team: str, month: str) -> int: ...
    async def increment(self, team: str, month: str, tokens: int) -> int: ...
    async def reset(self, team: str, month: str) -> None: ...
```

`SqliteQuotaStore` → `RedisQuotaStore` swapped via config. No callers change.

---

## Consequences

- Phase 1: no external infra required, quota race conditions possible under high concurrency (acceptable for POC)
- Phase 2: Redis required; document in README; acceptable tradeoff
- State store interface must be defined in Phase 1 to avoid refactor in Phase 2

---

## Alternatives Not Chosen

- **Postgres**: overkill; adds migration tooling for a quota counter
- **In-memory dict**: not persistent across restarts; doesn't survive server bounce during testing
- **Redis from day 1**: valid choice; deferred to reduce initial setup friction
