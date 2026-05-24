# Lessons Learned — Failure Mode Experiments

**Project:** Project 03 — Agentic Systems & MCP  
**Purpose:** Production mitigations for Orchid V3 design  
**Written:** 2026-05-23  
**Status:** Experiments 1–3, 5 designed + ready to run; Experiment 4 Part A verified.

Each section follows: **Setup → Observed / Expected behavior → Root cause → Production mitigation**

---

## Experiment 1: Researcher Tool Budget Exhaustion

**Script:** `experiments/exp1_budget_exhaustion.py`  
**Verification:** Code-inspected; run with `--part-a-only` equivalent logic verified.

### Setup
`max_tool_calls=1` on a 3-criterion task. One web search call is allowed;
the model receives the budget-exhaustion message and must synthesize from one call.

### Observed behavior (from code analysis)
- `finding.partial = True` — set when budget fires during the tool call loop
- `finding.confidence = "low"` — `_assess_confidence()` returns `"low"` on any partial
- `finding.gaps` includes `"Response is partial — tool call budget or time limit reached"`
  plus any success criteria whose keywords don't appear in the one-call content
- The synthesizer receives the finding with `[PARTIAL — budget or time limit reached]`
  qualifier injected into its prompt and is expected to note the gap

### Root cause
Budget enforcement is a hard stop: when `tool_calls_used >= effective_max_calls`,
subsequent tool calls in the same LLM response get `[Budget exhausted]` tool messages
and the wrap-up call fires immediately. The model gets one LLM call to summarize
whatever it gathered in a single tool call.

### What actually breaks
The synthesizer has no way to distinguish "low-confidence because the domain is uncertain"
from "low-confidence because the researcher ran out of budget." Both surface as
`confidence="low"` and `partial=True`. A downstream consumer can't tell whether
to re-queue the task or accept the uncertainty.

### Production mitigation (Orchid V3)
1. **Typed partial reason**: add a `partial_reason: Literal["budget", "time", "stall", None]`
   field to `ResearchFinding`. The synthesizer prompt and downstream routing can then
   distinguish "retry with more budget" from "inherently uncertain."
2. **Orchestrator-level retry**: if `finding.partial_reason == "budget"` and the pipeline
   has remaining token budget, re-queue the task with `max_tool_calls` doubled (up to a cap).
3. **Task-level budgets from the planner**: the planner should size `max_tool_calls` based
   on task complexity signals (number of success criteria, query breadth) rather than
   using a uniform default.

---

## Experiment 2: Garbage Tool Output (HTML instead of JSON)

**Script:** `experiments/exp2_garbage_tool_output.py`  
**Verification:** Code-inspected. Patch path verified (`src.agents.researcher.call_tool_safe`).

### Setup
`call_tool_safe` patched to always return `ToolResult(success=True, data="<html>...</html>")`.
Content is ~500 chars of an nginx 502 error page — repeated 3× to clearly exceed the 50-char
progress threshold.

### Expected behavior
- **Stall detection does NOT fire.** The HTML result is `success=True` and `len > 50` chars,
  so `calls_without_progress` resets to 0 on every call. The stall guard sees full "progress."
- **No `bad_output` error class.** `_classify_mcp_error()` in `wrapper.py` only fires on
  Python exceptions (`JSONDecodeError`, `ValidationError`, etc.). HTML returned as a successful
  string is invisible to the error classifier.
- **The model receives HTML as tool context.** Qwen3 will attempt to extract information from
  an nginx error page. Two likely outcomes:
  - **Hallucination path:** model extracts plausible-sounding but fabricated facts from
    the HTML boilerplate (e.g., infers the site is "nginx-powered" and extrapolates from there)
  - **Correct rejection path:** model notes "the tool returned an error page" and adjusts
    its search strategy. This depends on the model's instruction-following quality.
- `finding.confidence` is likely `"medium"` or `"high"` if the model produces coherent text —
  `_assess_confidence()` only checks `sources` count and `content` length, not factual accuracy.

### Root cause
Two gaps compound:
1. `call_tool_safe` validates at the MCP protocol level (`isError`) but not at the content level.
   Content-type mismatches (HTML from a web tool, binary from a file tool) pass through silently.
2. The progress stall detector uses content length as a proxy for "new information."
   A large garbage response looks like progress.

### Production mitigation (Orchid V3)
1. **Content-type validation in the wrapper**: for `web_search` and `fetch_page`, check if
   the result starts with `<!DOCTYPE` or `<html` and return
   `ToolResult(success=False, error_class="bad_output", error_message="Tool returned HTML instead of expected content")`.
2. **Schema validation per tool**: `web_search` should return a JSON array — validate it.
   `fetch_page` is less constrained (markdown/text is valid) but HTML boilerplate is detectable.
3. **Progress quality check**: instead of length alone, check whether the result was already
   seen (content hash). An error page served repeatedly is detectable.

---

## Experiment 3: Ambiguous Planner Input

**Script:** `experiments/exp3_ambiguous_planner.py`  
**Verification:** Code-inspected + overlap detector written.

### Setup
Three deliberately vague topics: `"Everything about AI"`, `"How does technology work?"`,
`"Tell me about programming"`.

### Expected behavior
- **The planner makes a best-guess decomposition** — there is no clarification mechanism.
  With `/no_think`, Qwen3 produces output quickly without extended reasoning.
- **Tasks will overlap.** A topic like `"Everything about AI"` might produce:
  - `"What is artificial intelligence?"` and `"What are the types of AI?"` — nearly the same.
  - Success criteria will be generic: `"Provide an overview"`, `"List examples"`.
- **The fallback task may fire** (`_fallback_task()`) if the model returns prose instead
  of a JSON array — plausible with very ambiguous topics that prompt explanatory responses.
- **Downstream effects**: overlapping tasks produce redundant findings. The synthesizer
  receives near-duplicate content and may produce a repetitive report. Confidence will be
  high (many sources, long content) even though the answer is shallow.

### Root cause
The planner prompt says "decompose into 2-4 discrete, focused research tasks" but offers no
mechanism to reject or refine an ambiguous input. With no clarification loop, the model
interpolates a reasonable decomposition from whatever the input implies. Vague inputs
yield vague interpolations.

### Production mitigation (Orchid V3)
1. **Planner confidence score**: have the planner return a `plan_confidence: float` alongside
   the tasks. If below a threshold (e.g., 0.6), surface this to the orchestrator and
   optionally block execution pending user clarification.
2. **Overlap detection before dispatch**: implement the word-overlap check from exp3's
   script in the orchestrator. If two tasks share >40% of significant words, merge or drop one.
3. **Input normalization**: for known ambiguous patterns ("everything about X",
   "tell me about X"), either reject with a clarification request or narrow to a default
   scope (e.g., "top 5 most-cited aspects of X").
4. **Planner self-critique step**: after generating tasks, ask the model in a second call
   to identify any overlapping or untestable tasks and rewrite them. This adds one LLM call
   but produces substantially better decompositions.

---

## Experiment 4: Kill Pipeline Mid-Run — Resume Without Data Loss

**Script:** `experiments/exp4_resume.py`  
**Verification: Part A run and verified** (2026-05-23). Part B requires LLM.

### Setup
Synthetic `PipelineState` with `status="researching"`, 2-task plan, `task_001` finding
already in `findings`, written to `state/exp4_*.json`. Orchestrator loaded with that `pipeline_id`.

### Observed behavior (Part A — verified)
```
SKIP  task_001 — already in findings ✓
RUN   task_002 — not yet completed
```
The skip logic fires correctly. `task_001` is not re-run. The state file on disk
is the recovered `PipelineState`; subsequent runs continue from `task_002`.

### Atomic write guarantee
`_persist()` writes to `{pipeline_id}.tmp` first, then `os.replace(tmp, final)`.
On POSIX, `os.replace` is atomic at the filesystem level. A kill signal between
`tmp.write_text()` and `os.replace()` leaves a `.tmp` orphan but does not corrupt
the main state file. The next run loads the last good state and re-runs the
in-progress task from scratch (one task may be duplicated, not lost).

### What actually breaks
- **The `.tmp` orphan**: if killed during the tmp write, the next run finds the last
  complete state (one task behind). The in-progress task runs again. This is safe
  but potentially expensive (one LLM task re-run per crash).
- **Synthesis is not idempotent at cost**: if killed during synthesis (status="synthesizing"),
  the next resume re-runs the full synthesis LLM call. Findings are not re-gathered,
  but one extra LLM call is paid.
- **No crash detection**: the orchestrator doesn't distinguish "crashed at status=researching"
  from "legitimately paused at status=researching." Both resume identically. This is fine
  for the PoC but would require a `started_at`/heartbeat mechanism in production.

### Production mitigation (Orchid V3)
1. **Idempotency key on synthesis**: cache the synthesizer output keyed by
   `hash(sorted(findings.values()))`. If the hash matches a stored output, skip the LLM call.
2. **Heartbeat / lease mechanism**: write a `{pipeline_id}.lock` with a TTL. If a pipeline's
   lock has expired, a monitor process can classify it as crashed and alert.
3. **`.tmp` cleanup on startup**: scan for orphaned `.tmp` files older than N minutes
   and remove them to prevent accumulation.

---

## Experiment 5: Task Exceeding Researcher Context Window

**Script:** `experiments/exp5_context_overflow.py`  
**Verification:** Code-inspected.

### Setup
`call_tool_safe` patched to return ~120KB of text from `fetch_page`. This is appended
to the message list as a tool result. With Qwen3-35B's practical context, multiple such
results will exceed the token limit before the budget is exhausted.

### Expected behavior
- **llama.cpp behavior is the key unknown.** Two possibilities:
  - **Silent truncation**: the server truncates the input and returns a response as if
    nothing happened. The model sees a partial message history and may hallucinate coherently.
  - **HTTP 400 / context length exceeded**: the server returns an error. `AsyncOpenAI` raises
    `openai.BadRequestError`. This exception propagates up through `ResearcherAgent.run()`
    uncaught — `ToolResult` only wraps MCP tool errors, not LLM API errors.
- If the exception propagates: the orchestrator's `except Exception` in `run()` catches it,
  calls `state.transition("failed")`, persists the error, and re-raises. The pipeline stops
  with `status="failed"` and `error="..."` in the state JSON. This is the correct
  failure-safe behavior, but it's accidental — the orchestrator wasn't designed to handle
  LLM API errors specifically.

### Root cause
The message list is unbounded. Each tool result is appended in full, with no truncation.
A single large `fetch_page` result can be 50–200KB. With a 32K token context (common for
Qwen3 on llama.cpp), three large fetches exhaust the window.

### Production mitigation (Orchid V3)
1. **Result truncation in the wrapper**: cap `result.data` at a configurable `max_result_chars`
   (e.g., 8000 chars). Append `"\n[TRUNCATED — {N} chars omitted]"` so the model knows.
   This is the highest-leverage fix: prevents the problem at the source.
2. **Message history pruning**: before each LLM call, estimate token count of the message list
   (rough: `len(json.dumps(messages)) / 4`). If approaching the context limit, drop the oldest
   tool result messages (keep system, user, and last N exchanges).
3. **Explicit LLM API error handling**: wrap the `await self.client.chat.completions.create(...)`
   call in a try/except for `openai.BadRequestError`. On context length error, prune the
   message history and retry once before propagating.

---

## Cross-Cutting Findings

### The error boundary is at the wrong layer

`ToolResult` is a clean error boundary for MCP tool failures. But LLM API errors — context
overflow, rate limits from the LLM backend, malformed responses — propagate as raw Python
exceptions. In a production system, LLM API calls need their own error boundary equivalent
to `call_tool_safe`.

### Confidence scoring is disconnected from factual accuracy

`_assess_confidence()` uses source count and content length as proxies. A researcher that
hallucinates 500 words of plausible-sounding text with 3 fabricated URLs scores `"high"`.
The metric measures *output volume*, not *output quality*. Any confidence signal passed to
a downstream system (Orchid V3 routing, user-facing UI) should treat these values as
"effort signals" not "accuracy signals."

### The planner and synthesizer share no feedback loop

The planner decomposes the topic once. If findings reveal that the decomposition was wrong
(tasks overlap, a critical subtopic was missed), there's no replanning. The synthesizer
absorbs the imperfect findings and produces a report regardless. For high-stakes research,
a reflection step (synthesizer assesses coverage gaps → planner adds tasks) would close this.

### Sequential orchestration makes all failures blocking

One failed or stalled researcher task blocks all subsequent tasks and synthesis.
In the 5-experiment surface area explored here, this is consistently the most painful
property: a context overflow in task 1 means tasks 2–4 never run, even if they're
perfectly scoped. Parallel research execution would contain blast radius to individual tasks.

---

## Orchid V3 Priority List

| Priority | Mitigation | Complexity | Experiment |
|----------|------------|------------|------------|
| P0 | Result truncation in wrapper (8K char cap) | Low | Exp 5 |
| P0 | `partial_reason` typed enum on `ResearchFinding` | Low | Exp 1 |
| P1 | Content-type validation for web tools | Medium | Exp 2 |
| P1 | LLM API error boundary (wrap completions call) | Medium | Exp 5 |
| P1 | Planner overlap detection before dispatch | Medium | Exp 3 |
| P2 | Parallel researcher execution | High | Sequential limitation |
| P2 | Planner self-critique step | Medium | Exp 3 |
| P3 | Synthesis idempotency cache | Low | Exp 4 |
| P3 | `.tmp` orphan cleanup on startup | Low | Exp 4 |
