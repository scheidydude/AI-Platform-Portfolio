# ADR-002 — Integration Pattern: Subclass with Post-Output Scan; Direct Test for Isolation

**Status:** Accepted  
**Date:** 2026-06-06  
**Deciders:** David Scheiderman

---

## Context

P06 must wire two P05 controls into P03's execution path:

1. **Content isolation** (`prepare_retrieved_context()`) — must run on external content before it enters the LLM context
2. **PII scanning** (`scan_output_for_pii()`) — must run on findings before they are persisted

The wiring approach depends on where in P03's architecture these hooks can be inserted without modifying P03 source files.

### P03 Architecture Facts (from reading `researcher.py` and `orchestrator.py`)

**Point 2 (PII scan)** is straightforward: `Orchestrator.run()` calls `self.researcher.run(task)` and receives a `ResearchFinding`. If `self.researcher` is a `SecureResearcherAgent` that scans findings before returning them, Point 2 is fully wired without touching orchestrator.py.

**Point 1 (content isolation)** is architecturally harder. P03's `ResearcherAgent.run()` is a 200-line method that:
- Manages an async `MultiServerClient` context
- Runs an agentic loop (up to `max_iterations` turns)
- On each turn: makes LLM API call, processes tool calls, appends `{"role": "tool", ..., "content": str(result.data)}` to messages inline

There is no overridable hook for tool result content before it enters messages. The only insertion points are:
1. Override the entire `run()` method (full copy) — fragile, defeats the "thin wrapper" premise
2. Override `_multi_server_client()` to inject a proxying client — complex, brittle
3. Test the P05 isolation function directly against inputs shaped like P03 tool results, rather than intercepting the live messages list

Additionally, P03's content source is fundamentally different from P05's design assumption:
- **P05 assumed:** Confluence/Jira retrieval → `RetrievedChunk` objects assembled before the LLM call
- **P03 actual:** MCP web search/fetch tool calls → `str` results inserted into conversation incrementally

This is an interface mismatch. The integration test can still verify the protective function (`prepare_retrieved_context()`) against inputs shaped like P03 tool results, but the live wiring of Point 1 inside the agentic loop requires a more invasive change.

---

## Options Considered

### Option A — Override `run()` with full copy-and-modify

Copy `ResearcherAgent.run()` into `SecureResearcherAgent` and add isolation wrapping at line 179 (tool result insertion).

**Pros:** Fully wires Point 1 in the live execution path.  
**Cons:** 200-line method copy; any upstream change to `researcher.py` silently diverges; completely defeats the "thin wrapper" premise; maintenance burden disproportionate to the portfolio signal.

**Rejected.**

### Option B — Proxy `MultiServerClient` to intercept tool results

Override `_multi_server_client()` to return a wrapper client that intercepts `call_tool_safe()` results and applies `isolate_chunk()` before returning.

**Pros:** Genuinely thin hook; preserves the agent loop.  
**Cons:** Requires deep knowledge of `MultiServerClient`'s internal call contract; the result format is a custom `ToolResult` dataclass; intercepting would require wrapping every method or monkey-patching. Complexity is high relative to the portfolio value of the wiring.

**Partially accepted:** Documented in `lessons-learned.md` as the right architectural pattern for a production system. P06 notes it as a future improvement.

### Option C (chosen) — Subclass for Point 2; direct test for Point 1

**Point 2 (PII scan):** `SecureResearcherAgent` overrides `run()` with a 5-line wrapper:

```python
async def run(self, task: ResearchTask) -> ResearchFinding:
    finding = await super().run(task)
    result = scan_output_for_pii(finding.content)
    if result.action == "block":
        raise PIIInFindingError(task.task_id, result.findings)
    if result.action == "warn":
        logger.warning("PII detected in finding %s — proceeding", task.task_id)
    return finding
```

**Point 1 (content isolation):** Test directly — no live wiring. `test_injection_defense.py` demonstrates:
- Given a `RetrievedChunk` built from a typical P03 MCP tool result shape
- `prepare_retrieved_context([chunk])` produces output with trust markers
- The same content without markers is indistinguishable from system context (the threat)
- With markers, the content is explicitly bounded (the defense)

`SecureOrchestrator` uses `SecureResearcherAgent` instead of `ResearcherAgent`.

**Pros:** Minimal code; honest about the architectural gap; tests prove the function's protective value even without live wiring; Point 2 is fully wired end-to-end.  
**Cons:** Point 1 live wiring is deferred; requires the test to be clear about what it is and is not exercising.

---

## Decision

**Option C.**

The portfolio signal from this project is: "I understand where controls must be inserted, what the interface contracts are, and where architectural constraints prevent a clean hook." Documenting the gap honestly in the ADR and lessons-learned is more valuable to a hiring reviewer than a 200-line method copy that obscures the analysis.

The test for Point 1 is designed to make the threat and the defense concrete, even without live pipeline wiring. The distinction is made explicit in the test docstring and in `docs/integration-surface.md`.

---

## Consequences

- `SecureResearcherAgent` is a 15-line class, not a copy of `researcher.py`
- Point 2 (PII scan) is fully wired and exercised end-to-end
- Point 1 (content isolation) is demonstrated via direct function testing, not pipeline interception
- `docs/lessons-learned.md` documents the proxy pattern (Option B) as the correct production approach
- If P03 adds an overridable hook in a future refactor, Option B can be adopted with no changes to the P05 control
