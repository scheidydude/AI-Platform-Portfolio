# ADR-005 — Rate Limiting: In-Memory Sliding Window

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

Need per-team RPM (requests per minute) rate limiting to prevent any single team from flooding the gateway and starving others — even if they're still within their token budget. Token quota and request rate are orthogonal concerns: a team could send 1,000 tiny requests per minute that each consume few tokens.

Rate limiting state has different characteristics than quota state:
- **Quota** state must survive restarts (monthly counters matter)
- **Rate limit** state is ephemeral (a per-minute window resets anyway)

---

## Decision

**In-memory sliding window per team. Single `deque[float]` of request timestamps.**

---

## Rationale

### Why in-memory

Rate limiting windows are 60 seconds. If the process restarts, the window is empty — which is acceptable. The worst case is a brief window where a team gets a free minute of requests after a restart. Compared to the operational overhead of Redis for this specific use case, the tradeoff is clear.

SQLite would work but adds async I/O on every request just to enforce a 60-second window. The per-request overhead is unnecessary.

### Why sliding window over fixed window

Fixed window (e.g., "60 requests per minute, reset on the minute boundary") has a burst vulnerability: a team can send 60 requests at 00:59 and 60 more at 01:01, getting 120 requests in 2 seconds. Sliding window prevents this by always looking at the last 60 seconds from *now*.

### Why not token bucket / leaky bucket

Token bucket is correct and efficient but requires more code for marginal benefit at POC scale. Sliding window with `deque` is equally correct for typical RPM limits (≤ a few hundred) and trivially readable.

### Concurrency safety

Python's asyncio is single-threaded. Two coroutines cannot run `check_and_record` concurrently — an `await` must be hit to yield control, and our rate limit check has no `await`. The deque operations are atomic within a single event loop turn.

---

## Consequences

- Rate limit state is lost on process restart (acceptable for POC)
- Does not work across multiple gateway instances (would need Redis for distributed deployments)
- Memory footprint: one `float` per request in the sliding window per team — negligible
- Upgrade path for distributed: replace `RateLimiter` with a Redis `ZADD`/`ZREMRANGEBYSCORE` implementation behind the same interface

---

## Upgrade Path (future)

```python
class RedisRateLimiter:
    async def check_and_record(self, team: str, rpm_limit: int) -> bool:
        now = time.time()
        key = f"ratelimit:{team}"
        async with redis.pipeline() as pipe:
            pipe.zremrangebyscore(key, 0, now - 60)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, 60)
            _, count, *_ = await pipe.execute()
        if count >= rpm_limit:
            # undo the zadd
            await redis.zrem(key, str(now))
            return False
        return True
```

---

## Alternatives Not Chosen

- **Redis ZADD sliding window**: correct for distributed; overkill for single-process POC
- **Fixed window counter**: simpler but burst-vulnerable at boundaries
- **Token bucket**: more nuanced burst handling; unnecessary complexity for POC RPM limits
