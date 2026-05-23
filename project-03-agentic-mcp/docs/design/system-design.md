# System Design — Project 03: Agentic Systems & MCP

**Version:** 0.1 (draft)  
**Author:** David Scheiderman  
**Date:** 2026-05-23  
**Status:** Draft — updated as decisions are made

---

## 1. Overview

3-agent research pipeline. User submits a natural-language research question. The pipeline decomposes it, executes research via real MCP tools, and synthesizes a cited report.

```
User
 │
 ▼
┌─────────────────┐
│  Planner Agent  │  ← pure reasoning, no tools
│                 │  Input:  NL research request
│                 │  Output: list[ResearchTask]
└────────┬────────┘
         │ list[ResearchTask]
         ▼
┌─────────────────────────────────┐
│       Researcher Agent(s)       │  ← one invocation per task
│                                 │  Input:  ResearchTask
│  Tools:                         │  Output: ResearchFinding
│  - web_search (Brave/Tavily)    │
│  - fetch_page                   │
│  - github: search_repositories  │
│  - github: get_file_contents    │
│  - github: search_code          │
└────────┬────────────────────────┘
         │ list[ResearchFinding]
         ▼
┌─────────────────┐
│ Synthesizer     │  ← pure reasoning, no tools
│ Agent           │  Input:  all ResearchFindings
│                 │  Output: final report (cited, gaps flagged)
└─────────────────┘
         │
         ▼
      Report
```

---

## 2. Agent Roles

### Planner Agent

| Attribute | Value |
|-----------|-------|
| Input | Natural-language research request |
| Output | `list[ResearchTask]` |
| Tools | None |
| Constraints | `AgentConstraints` (max_iterations, max_wall_time_seconds) |

Responsibility: decompose ambiguous user requests into concrete, actionable tasks with explicit success criteria. Each task must be independently executable by a Researcher.

### Researcher Agent

| Attribute | Value |
|-----------|-------|
| Input | Single `ResearchTask` |
| Output | `ResearchFinding` |
| Tools | Web search MCP, GitHub MCP |
| Constraints | `AgentConstraints` (max_tool_calls from task, max_iterations, max_wall_time_seconds) |

Responsibility: execute one task. Track tool call history to prevent infinite retry loops. Wrap all tool calls in `ToolResult`. Return partial finding on constraint exhaustion.

### Synthesizer Agent

| Attribute | Value |
|-----------|-------|
| Input | `list[ResearchFinding]` |
| Output | Final report |
| Tools | None |
| Constraints | `AgentConstraints` |

Responsibility: combine findings into coherent response. Flag low-confidence findings, missing sources, and gaps explicitly.

---

## 3. Data Flow

```
NL Request
    → Planner → list[ResearchTask]
    → [foreach task] Researcher → ResearchFinding
    → Synthesizer → Report
```

State is persisted after each transition. Pipeline can resume from any completed `ResearchTask`.

---

## 4. Data Models

_Full Pydantic schemas defined in `src/models.py` (when created). Summarized here._

### ResearchTask
```python
class ResearchTask(BaseModel):
    task_id: str                    # uuid
    description: str
    success_criteria: list[str]
    max_tool_calls: int = 5
    assigned_to: str = "researcher"
```

### ResearchFinding
```python
class ResearchFinding(BaseModel):
    task_id: str
    content: str
    sources: list[Source]
    confidence: Literal["high", "medium", "low"]
    gaps: list[str]
    tool_calls_used: int
```

### Source
```python
class Source(BaseModel):
    url: str | None
    title: str
    tool: str                       # which MCP tool produced this
    retrieved_at: datetime
```

### AgentConstraints
```python
class AgentConstraints(BaseModel):
    max_tool_calls: int
    max_iterations: int
    max_wall_time_seconds: int
    on_exceed: Literal["fail", "return_partial", "escalate"]
```

### PipelineState
```python
class PipelineState(BaseModel):
    pipeline_id: str
    status: Literal["planning", "researching", "synthesizing", "complete", "failed"]
    plan: list[ResearchTask]
    findings: dict[str, ResearchFinding]   # task_id → finding
    started_at: datetime
    updated_at: datetime
    error: str | None = None
```

### ToolResult
```python
class ToolResult(BaseModel):
    success: bool
    data: Any | None
    error_class: Literal["rate_limit", "not_found", "timeout", "bad_output", "unavailable"] | None
    error_message: str | None
    retries_attempted: int = 0
```

---

## 5. Tool Error Handling

See [docs/design/tool-error-handling.md](tool-error-handling.md) (when created) for full strategy.

Summary: all tool calls return `ToolResult`. No raw exceptions reach agent context.

| Error class | HTTP/signal | Strategy |
|-------------|-------------|----------|
| rate_limit | 429 | Exponential backoff + jitter, max 3 retries |
| not_found | 404 | Mark `confidence="low"`, continue |
| timeout | timeout | Log, mark unavailable, no inline retry |
| bad_output | schema mismatch | Validate, reformat once, skip |
| unavailable | connection error | Fail gracefully, gap in synthesizer |

---

## 6. Loop Prevention

See [docs/design/loop-prevention.md](loop-prevention.md) (when created) for full design.

Summary:
- Duplicate tool call detection: `(tool_name, hash(args))` tracked per task
- Progress stall detection: every N calls, check if `content` field grew
- Forward-only agent flow: no back-edges in pipeline graph
- All agents start with explicit `AgentConstraints`

---

## 7. Orchestration

Sequential (Phase 4). See ADR-005.

```
PipelineState: planning
  → Planner runs → emits ResearchTask list
PipelineState: researching
  → foreach task: Researcher runs → emits ResearchFinding
  → PipelineState.findings updated + persisted after each task
PipelineState: synthesizing
  → Synthesizer runs over all findings
PipelineState: complete | failed
```

---

## 8. MCP Integrations

_Details finalized in Phase 2. Placeholder._

| MCP Server | Tools | Provider |
|------------|-------|----------|
| Web search | `web_search`, `fetch_page` | TBD (ADR-003) |
| GitHub | `search_repositories`, `get_file_contents`, `search_code` | github MCP server |

---

## 9. Open Questions

| Question | Owner | Target resolution |
|----------|-------|-------------------|
| Language/framework? | David | Phase 1 (ADR-001) |
| MCP client library? | David | Phase 1 (ADR-002) |
| Web search provider? | David | Phase 1 (ADR-003) |
| State persistence (JSON vs SQLite)? | David | Phase 1 (ADR-004) |
| Parallel researcher tasks within sequential? | David | Phase 4 eval |

---

## 10. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-05-23 | Initial draft — data models, agent roles, orchestration sketch |
