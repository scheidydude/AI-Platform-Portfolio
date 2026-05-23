# Task Plan — Project 03: Agentic Systems & MCP

**Goal:** 3-agent pipeline (planner → researcher → synthesizer) wired to GitHub MCP + web search MCP  
**Started:** 2026-05-23  
**Duration:** 10 days (~2026-06-02)

---

## Phases

| # | Phase | Status | Days | Notes |
|---|-------|--------|------|-------|
| 1 | Architecture design | `complete` | 1–2 | All ADRs accepted 2026-05-23 |
| 2 | MCP wiring | `complete` | 3–4 | SearXNG MCP server + Researcher agent |
| 3 | Loop prevention | `not_started` | 5–6 | Escape conditions, retry tracking |
| 4 | Orchestration | `not_started` | 7–8 | Sequential first, then streaming eval |
| 5 | Failure mode docs | `not_started` | 9–10 | Deliberate breaks + lessons learned |

---

## Phase 1 — Architecture Design

**Status:** `complete`  
**Goal:** Answer all agent definition + handoff schema questions before writing code

### Decisions needed
- [x] Language/framework (Python assumed — confirm)
- [x] MCP client library (pick one: `mcp` SDK, `anthropic-sdk` tool use, other)
- [x] Web search MCP: Brave Search vs Tavily
- [x] State persistence: disk (JSON) vs SQLite
- [x] Async vs sync orchestration

### Schemas to define
- [x] `ResearchTask` (Planner output)
- [x] `ResearchFinding` (Researcher output)
- [x] `AgentConstraints` (escape conditions)
- [x] `PipelineState` (orchestration state)
- [x] `ToolResult` (error wrapper)

### Deliverable
Architecture doc or annotated schema file — answers all 5 questions, all schemas defined.

---

## Phase 2 — MCP Wiring

**Status:** `complete`  
**Goal:** Researcher agent working with one MCP tool (web search first, then GitHub)

### Tasks
- [x] Set up MCP server(s)
- [x] Wire `web_search` tool to Researcher agent
- [x] Wire `fetch_page` tool
- [x] Wire GitHub: `search_repositories`, `get_file_contents`, `search_code`
- [x] Implement `ToolResult` wrapper (structured error, never raw exception)
- [x] Handle all 5 failure classes (429, 404, timeout, bad output, unavailable)

### Failure class table
| Class | Strategy |
|-------|----------|
| 429 | Exponential backoff + jitter, max 3 retries |
| 404 | Low-confidence, continue |
| Timeout | Log, mark unavailable, no inline retry |
| Bad output | Validate schema, reformat once, skip |
| Unavailable | Fail gracefully, inform synthesizer |

---

## Phase 3 — Loop Prevention

**Status:** `not_started`  
**Goal:** All 3 loop types handled with explicit escape conditions

### Loop types
- [ ] Infinite retry: track `(tool_name, args_hash)` per task, escalate on dup
- [ ] Progress stall: progress check every N calls, escape if no new info
- [ ] Circular delegation: enforce forward-only flow (no back-edges)

### Escape conditions
Every agent gets `AgentConstraints(max_tool_calls, max_iterations, max_wall_time_seconds, on_exceed)`  
Default `on_exceed`: `"return_partial"` — partial answer with gaps > silent fail

---

## Phase 4 — Orchestration

**Status:** `not_started`  
**Goal:** Sequential pipeline working end-to-end; evaluate streaming

### Tasks
- [ ] Sequential orchestrator: Planner → Researcher (tasks) → Synthesizer
- [ ] `PipelineState` persisted to disk/SQLite after every transition
- [ ] Resume from last completed task without re-running earlier work
- [ ] Document what breaks in sequential
- [ ] Evaluate: is streaming worth added complexity?

---

## Phase 5 — Failure Mode Documentation

**Status:** `not_started`  
**Goal:** Deliberate experiments → lessons learned doc for Orchid V3

### Experiments
- [ ] Exhaust researcher tool budget mid-task — what does synthesizer do?
- [ ] Inject garbage tool output (HTML instead of JSON) — hallucinate or handle?
- [ ] Ambiguous planner input — clarify or bad assumption?
- [ ] Kill pipeline mid-run — resume without data loss?
- [ ] Task exceeding researcher context window — what breaks?

### Deliverable
`lessons_learned.md` — findings + production mitigation for each failure mode

---

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |

---

## Deliverables Checklist

- [ ] Working 3-agent pipeline
- [ ] GitHub MCP + web search MCP wired and tested
- [ ] Typed handoff schemas
- [ ] Tool error handling (all 5 failure classes)
- [ ] Loop prevention + escape conditions
- [ ] Resumable pipeline state
- [ ] Failure mode experiment docs
- [ ] `lessons_learned.md` for Orchid V3
