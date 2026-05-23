# Software Requirements Specification
## Project 03 — Agentic Systems & MCP

**Version:** 0.1 (draft)  
**Author:** David Scheiderman  
**Date:** 2026-05-23  
**Status:** Draft

---

## 1. Purpose

Build and document a 3-agent research pipeline wired to real MCP servers. This is a deliberate stress-test of multi-agent design patterns — specifically state handoff, tool error handling, and loop prevention — to inform the design of Orchid V3.

---

## 2. Scope

### In scope
- Planner agent: decomposes natural-language research requests into structured task lists
- Researcher agent: executes individual tasks using MCP tools (web search + GitHub)
- Synthesizer agent: combines researcher outputs into a coherent report with citations
- MCP integrations: GitHub MCP (search, file read, code search) + web search MCP (Brave or Tavily)
- Typed handoff schemas between all agents
- Tool error handling for all 5 failure classes
- Loop prevention with explicit escape conditions
- Resumable pipeline state (persist to disk/SQLite)
- Failure mode experiment documentation
- Lessons learned doc for Orchid V3

### Out of scope
- Production deployment / hosting
- Authentication / multi-user support
- UI / frontend
- Agent fine-tuning

---

## 3. Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| David Scheiderman | Builder / learner | Career documentation, functional PoC |
| Orchid V3 (future) | Consumer of lessons | Architectural inputs |

---

## 4. Functional Requirements

### FR-01 — Planner Agent
- **FR-01.1** Accept natural-language research request as input
- **FR-01.2** Decompose into structured `ResearchTask` list with success criteria per task
- **FR-01.3** Define `max_tool_calls` per task
- **FR-01.4** Produce typed output conforming to `ResearchTask` schema
- **FR-01.5** Use no external tools (pure reasoning)

### FR-02 — Researcher Agent
- **FR-02.1** Accept single `ResearchTask` as input
- **FR-02.2** Execute task using available MCP tools (web search and/or GitHub)
- **FR-02.3** Produce structured `ResearchFinding` with source refs and confidence level
- **FR-02.4** Respect `max_tool_calls` constraint from task definition
- **FR-02.5** Handle all 5 tool failure classes without propagating raw exceptions

### FR-03 — Synthesizer Agent
- **FR-03.1** Accept all `ResearchFinding` outputs as input
- **FR-03.2** Produce coherent report with citations, gaps flagged, and overall confidence
- **FR-03.3** Use no external tools (pure reasoning over provided context)
- **FR-03.4** Flag findings with `"low"` confidence or missing sources explicitly

### FR-04 — MCP Tool Integration
- **FR-04.1** GitHub MCP: `search_repositories`, `get_file_contents`, `search_code`
- **FR-04.2** Web search MCP: `web_search`, `fetch_page`
- **FR-04.3** All tool calls wrapped in `ToolResult` — structured outcome, never raw exception

### FR-05 — Tool Error Handling
- **FR-05.1** 429 (rate limit): exponential backoff + jitter, max 3 retries
- **FR-05.2** 404 (not found): mark low-confidence, continue
- **FR-05.3** Timeout: log, mark source unavailable, no inline retry
- **FR-05.4** Bad output: validate schema, reformat once, skip on second failure
- **FR-05.5** Tool unavailable: fail gracefully, communicate gap to synthesizer

### FR-06 — Loop Prevention
- **FR-06.1** Track `(tool_name, args_hash)` per task; escalate on duplicate call
- **FR-06.2** Progress check every N tool calls; escape if no new information added
- **FR-06.3** Enforce forward-only agent flow: Planner → Researcher → Synthesizer (no back-edges)
- **FR-06.4** Every agent has `AgentConstraints` defined before execution

### FR-07 — Orchestration
- **FR-07.1** Sequential orchestration: Planner completes → Researcher runs tasks → Synthesizer runs
- **FR-07.2** `PipelineState` persisted to disk/SQLite after every state transition
- **FR-07.3** Pipeline resumable from last completed task without re-running earlier work

### FR-08 — Documentation
- **FR-08.1** All architectural decisions captured in ADR format before implementation
- **FR-08.2** All 5 failure mode experiments run and results documented
- **FR-08.3** `lessons-learned.md` produced as bridge to Orchid V3 planning

---

## 5. Non-Functional Requirements

| ID | Requirement | Rationale |
|----|-------------|-----------|
| NFR-01 | All agent state serializable | Required for resume (FR-07.3) |
| NFR-02 | No raw exceptions reach agent context | Error handling completeness |
| NFR-03 | `return_partial` preferred over silent fail | Better than nothing in production-like systems |
| NFR-04 | All handoff schemas typed (Pydantic or TypedDict) | Sloppy handoffs are #1 multi-agent failure cause |
| NFR-05 | Codebase runnable from single entry point | Reproducibility for portfolio review |

---

## 6. Constraints

- Learning project — code quality valued, but simplicity over premature abstraction
- 10-day build window (2026-05-23 → 2026-06-02)
- MCP servers must be real (not mocked) for Phase 2 validation
- Deliberate failure injection required in Phase 5

---

## 7. Data Models (Summary)

Full schemas in [docs/design/handoff-schemas.md](design/handoff-schemas.md) (when created).

| Model | Owner | Description |
|-------|-------|-------------|
| `ResearchTask` | Planner output | Task definition with success criteria |
| `ResearchFinding` | Researcher output | Finding with sources and confidence |
| `AgentConstraints` | All agents | Escape conditions per agent |
| `PipelineState` | Orchestrator | Full resumable pipeline state |
| `ToolResult` | Tool wrapper | Structured outcome, never raw exception |
| `Source` | Researcher | Source reference for citations |

---

## 8. Success Criteria

| Criterion | How verified |
|-----------|-------------|
| Pipeline runs end-to-end on a real research query | Manual test run |
| GitHub MCP + web search MCP both exercised | Tool call logs |
| All 5 tool failure classes handled | Unit/integration tests |
| Pipeline resumable after mid-run kill | Experiment #4 in Phase 5 |
| All ADRs accepted | Doc index |
| `lessons-learned.md` complete | Content review |

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-05-23 | David Scheiderman | Initial draft |
