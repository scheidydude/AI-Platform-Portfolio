# Loop Prevention Design

**Status:** complete  
**Scope:** `src/agents/researcher.py` — Phase 3 hardening  
**Written:** 2026-05-23

---

## Problem

The Researcher has two partially-implemented loop guards:

| Guard | Implemented | Gap |
|-------|-------------|-----|
| Duplicate call detection | Yes — `seen_calls` set on `(tool_name, args_hash)` | Catches identical calls; misses different calls with no useful output |
| Progress stall detection | No | Agent can exhaust budget calling varied tools that return nothing new |
| Circular delegation prevention | N/A (one agent) | Deferred to Phase 4 |

This doc covers the one missing piece: **progress stall detection**.

---

## Definition of "Progress"

A tool call counts as progress if `result.success == True` and `len(str(result.data)) > 50`.

Rationale:
- Error results (`result.success == False`) carry no new information by definition.
- Results under 50 chars are typically empty, "not found", or boilerplate — not substantive data.
- We do NOT compare result content to previous results. Content deduplication would require O(N) comparisons and misses the common case where each call returns slightly different boilerplate from the same dead end.
- We do NOT use `sources` length as the proxy. GitHub tools (`search_code`, `get_file_contents`) don't add to `sources` (no URL). A productive GitHub-heavy run would incorrectly trigger stall detection.

---

## Detection Mechanism

Track two counters in `run()`:

```
calls_without_progress: int = 0
stall_warnings_sent: int = 0
```

After each tool call resolves:
- If the call counts as progress: `calls_without_progress = 0`
- Otherwise: `calls_without_progress += 1`

When `calls_without_progress >= stall_window` (default 3):
1. Inject a stall warning into `messages` (role=`user`)
2. Reset `calls_without_progress = 0`
3. Increment `stall_warnings_sent`
4. If `stall_warnings_sent >= 2`: set `partial = True`, break → force summary

The stall warning message text:
```
[Stall detected] Your last {stall_window} tool calls returned no useful data.
Either conclude with what you have found so far, or try a substantially different approach.
```

---

## Configuration

Add `stall_window: int = 3` to `AgentConstraints` in `src/models.py`.

This is an additive field — no existing field names change. Default value (3) matches "last N calls" semantic described in Phase 3 requirements.

Two stall warnings before forced termination gives the model one recovery attempt. A single warning risks terminating a legitimately slow start (first 3 calls all timeout). Two warnings with a reset window between them provides a meaningful second chance.

---

## Warning Injection vs. Budget Exhaustion

Stall detection is **not** budget exhaustion. Differences:

| | Budget exhaustion | Stall detection |
|-|-------------------|-----------------|
| Trigger | `tool_calls_used >= effective_max_calls` | `calls_without_progress >= stall_window` |
| First response | Inject budget message, force summary immediately | Inject stall warning, continue loop |
| `partial` flag | Set on first trigger | Set only on second consecutive stall |
| Model gets to recover | No | Yes (one chance) |

---

## Interaction with Existing Guards

**Duplicate call detection:** A duplicate call does NOT increment `calls_without_progress` because the duplicate path `continue`s before the result is evaluated. This is correct — a duplicate call is already handled by its own warning; we don't double-penalize.

**Wall time:** Wall time check runs at the top of the while loop, before stall evaluation. Wall time always wins. Stall detection is irrelevant if wall time fires first.

**Budget:** Budget check runs per tool call inside the loop. Budget can fire before stall threshold is reached. The two guards are independent.

---

## Implementation Checklist

- [x] Add `stall_window: int = 3` to `AgentConstraints` in `src/models.py`
- [x] Add `calls_without_progress` and `stall_warnings_sent` counters in `researcher.py run()`
- [x] After each tool result: update `calls_without_progress`
- [x] On stall threshold: inject warning, reset counter, increment `stall_warnings_sent`
- [x] On second stall: set `partial = True`, break
- [x] Skip counter update for duplicate-detected calls (they `continue` before this point — no change needed)

---

## What This Does Not Cover

- **Circular delegation** (Planner → Researcher → Planner loop): deferred to Phase 4. `PipelineState` enforces forward-only status transitions at schema level; runtime enforcement is an Orchestrator concern.
- **Content deduplication across calls**: not implemented. The 50-char threshold is a sufficient proxy for this PoC.
- **Adaptive stall window**: fixed at `stall_window`. No per-task override. Could be added to `ResearchTask` later if needed.
