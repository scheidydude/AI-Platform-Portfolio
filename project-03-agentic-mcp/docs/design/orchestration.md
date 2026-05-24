# Orchestration Design

**Status:** complete  
**Scope:** `src/orchestrator.py`, `src/agents/planner.py`, `src/agents/synthesizer.py`  
**Written:** 2026-05-23

---

## Sequential Pipeline

```
topic
  │
  ▼
PlannerAgent.run(topic) → list[ResearchTask]
  │  state → "researching", persisted
  ▼
for each task:
  ResearcherAgent.run(task) → ResearchFinding
  state.findings[task_id] = finding, persisted
  │
  ▼ (all tasks done)
state → "synthesizing", persisted
  │
  ▼
SynthesizerAgent.run(topic, plan, findings) → str (markdown report)
  │
  ▼
state → "complete", persisted
```

Every arrow is a `PipelineState.transition()` call — backward moves raise `ValueError`.

---

## State Persistence

After every transition and after every `ResearchFinding` is saved:
- Write to `state/{pipeline_id}.json` via atomic `os.replace(tmp → final)`
- File is valid JSON at all times (no partial writes)
- On resume: load state, skip tasks already in `state.findings`

This satisfies ADR-004 (JSON to disk, atomic write). If the process dies mid-research, the next run with the same `pipeline_id` skips all completed tasks.

---

## Resume

```bash
uv run python main.py "topic" <pipeline_id>
```

The orchestrator loads `state/{pipeline_id}.json`. Tasks whose `task_id` is already in `findings` are skipped. Research resumes from the first incomplete task. Synthesis re-runs if status was `"synthesizing"` at crash time (idempotent — findings are complete, only the LLM call is re-done).

---

## What Breaks in Sequential

**No parallelism.** Research tasks run one at a time. A 4-task plan with 6 tool calls each takes 4× the latency of a single task. If tasks are independent (they usually are — the planner decomposes by subtopic), they could all run concurrently.

**Blocking on slow tasks.** One slow researcher call blocks the entire pipeline. There's no timeout at the orchestrator level — only the per-task `max_wall_time_seconds` inside `ResearcherAgent`.

**No mid-pipeline replanning.** The planner runs once. If an early finding reveals that the decomposition was wrong (e.g., two tasks overlap heavily, or a key topic was missed), there's no mechanism to adjust the plan. The synthesizer absorbs the imperfect findings.

**Synthesizer context grows with task count.** Each `ResearchFinding.content` is passed verbatim to the synthesizer. With 4 tasks at 1000 chars each + sources, the synthesizer prompt approaches 6–8 KB. Not a problem at this scale; could hit context limits with many tasks or large findings.

**Single-point error propagation.** If any `ResearcherAgent.run()` raises (not `partial`, but an actual exception — e.g., the llama.cpp server is down), the orchestrator transitions to `"failed"` and the whole pipeline stops. There's no per-task retry at the orchestrator level.

---

## Streaming Evaluation: Is It Worth the Complexity?

**Verdict for this PoC: No.**

### What streaming would add
- The synthesizer could begin writing the report while the last researcher call is still running
- The caller sees partial output incrementally rather than waiting for the full synthesis
- Token-to-first-byte latency drops significantly for the report

### Why it's not worth it here

**Resume logic becomes harder.** Streaming requires tracking which tokens have been emitted, not just which tasks are complete. Partial stream state is harder to serialize than a `ResearchFinding` object.

**The bottleneck isn't synthesis.** Synthesis is one fast LLM call (~5–10s). Research is the slow part (multiple tool calls, wall time up to 120s per task). Streaming synthesis shaves seconds off a minutes-long pipeline — not the right optimization.

**Only one consumer.** The pipeline currently terminates at `main.py` print. Streaming adds complexity (async generators, backpressure) that has no consumer to benefit from it.

**Deferred to Phase 4 experiments (Phase 5).** If Phase 5 tests reveal that synthesis latency is a pain point, revisit. The interface is `SynthesizerAgent.run() → str`; swapping to `run() → AsyncIterator[str]` is a contained change.

---

## Implementation Checklist

- [x] `PlannerAgent` — single LLM call, JSON array → `list[ResearchTask]`, fallback on parse failure
- [x] `SynthesizerAgent` — single LLM call, all findings → markdown report
- [x] `Orchestrator.run()` — sequential Planner → Researcher(s) → Synthesizer
- [x] `_persist()` — atomic JSON write via `os.replace()`
- [x] Resume — skip tasks already in `state.findings`
- [x] Error handling — transition to `"failed"`, persist error message
- [x] `main.py` — updated to run full pipeline, supports `pipeline_id` resume arg
