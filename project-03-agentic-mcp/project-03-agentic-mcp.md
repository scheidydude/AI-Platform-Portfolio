# Project 3 — Agentic Systems & MCP
**Skill area:** Agentic systems and MCP  
**Format:** Homelab build  
**Estimated duration:** 10 days

---

## Overview

Build a 3-agent pipeline — planner, researcher, synthesizer — wired to real MCP servers. At minimum: GitHub and a web search tool (Brave Search or Tavily). This pushes you on agent handoff patterns, tool error handling, and loop prevention. Think of it as a deliberate stress test and architectural probe for Orchid's design.

---

## The mental model

Multi-agent systems fail in predictable ways:

- **Agents lose state** between handoffs
- **Tool errors** are not handled gracefully — the agent retries forever or silently fails
- **Agents loop** when they cannot make progress and have no escape condition
- **Handoff schemas** are too loose — Agent B doesn't know what Agent A actually produced

This project is specifically designed to surface all four failure modes so you can design around them.

---

## Phase 1 — Architecture design (Days 1–2)

Before writing code, design the system on paper. You should be able to answer all of the following before Day 3.

### Agent definitions

**Planner agent**
- Input: user research request (natural language)
- Responsibility: decompose into a structured research plan with discrete tasks
- Output: typed task list with success criteria per task
- Tools: none (pure reasoning)

**Researcher agent**
- Input: single task from the plan
- Responsibility: execute the task using available tools
- Output: structured finding with source references and confidence level
- Tools: web search MCP, GitHub MCP (optionally: Jira, Confluence)

**Synthesizer agent**
- Input: all researcher outputs
- Responsibility: produce a coherent answer with citations, gaps flagged, and confidence assessment
- Output: structured report with citations
- Tools: none (pure reasoning over provided context)

### Handoff schema

Define a typed schema for agent-to-agent communication. Use Pydantic or plain TypedDict. Sloppy handoffs are the number one cause of multi-agent failures.

```python
class ResearchTask(BaseModel):
    task_id: str
    description: str
    success_criteria: list[str]
    max_tool_calls: int = 5
    assigned_to: str = "researcher"

class ResearchFinding(BaseModel):
    task_id: str
    content: str
    sources: list[Source]
    confidence: Literal["high", "medium", "low"]
    gaps: list[str]
    tool_calls_used: int
```

---

## Phase 2 — MCP wiring (Days 3–4)

### MCP servers to integrate

**GitHub MCP** — minimum viable tools to wire up:
- `search_repositories` — find relevant repos
- `get_file_contents` — read specific files
- `search_code` — search across code

**Web search MCP** — use Brave Search or Tavily:
- `web_search` — general query
- `fetch_page` — retrieve full page content from a URL

**Why these two?** They represent the two main tool categories you will encounter in enterprise agent work: structured API tools (GitHub) and unstructured web tools (search). The failure modes are different and both are worth experiencing.

### Tool error handling — the hard part

Implement explicit handling for every tool failure class:

| Failure class | Handling strategy |
|---|---|
| Rate limit (429) | Exponential backoff with jitter, max 3 retries |
| Not found (404) | Mark task as low-confidence, continue |
| Timeout | Log, mark source as unavailable, do not retry inline |
| Bad output | Validate schema, ask model to reformat once, then skip |
| Tool unavailable | Fail gracefully, inform synthesizer of gap |

Build a `ToolResult` wrapper that always produces a structured outcome — never let a raw exception propagate to the agent's context.

---

## Phase 3 — Loop prevention (Days 5–6)

This is the most underestimated problem in agentic systems.

### Loop types to handle

**Infinite retry loop** — agent keeps calling the same tool with the same args hoping for a different result.  
Fix: track `(tool_name, args_hash)` pairs per task. If the same call appears twice, escalate.

**Progress stall** — agent is making tool calls but not advancing toward the success criteria.  
Fix: implement a progress check every N tool calls. If no new information has been added to the finding, trigger an escape condition.

**Circular delegation** — agents passing tasks back and forth.  
Fix: tasks can only flow forward in the pipeline (Planner → Researcher → Synthesizer). No back-edges.

### Escape conditions

Every agent must have explicit escape conditions defined before execution begins:

```python
class AgentConstraints(BaseModel):
    max_tool_calls: int
    max_iterations: int
    max_wall_time_seconds: int
    on_exceed: Literal["fail", "return_partial", "escalate"]
```

The `return_partial` option is the most realistic for a production system — it is better to return a partial answer with gaps flagged than to fail silently or run forever.

---

## Phase 4 — Orchestration (Days 7–8)

### Coordination patterns

Implement and compare two orchestration approaches:

**Sequential** — Planner completes fully, then Researcher runs all tasks (optionally in parallel), then Synthesizer runs. Simple to reason about, easier to debug.

**Streaming** — Researcher tasks feed into Synthesizer incrementally as they complete. More complex, better latency, harder to manage state.

Start with sequential. Document what breaks. Then consider whether streaming is worth the complexity for your use case.

### State management

All agent state must be serializable and recoverable. If the pipeline fails midway through, you should be able to resume from the last completed task without re-running earlier work.

```python
class PipelineState(BaseModel):
    pipeline_id: str
    status: Literal["planning", "researching", "synthesizing", "complete", "failed"]
    plan: list[ResearchTask]
    findings: dict[str, ResearchFinding]  # task_id → finding
    started_at: datetime
    updated_at: datetime
    error: str | None = None
```

Persist this to disk or SQLite after every state transition. This is your resume point.

---

## Phase 5 — Failure mode documentation (Days 9–10)

Deliberately break things and document what you find.

### Experiments to run

1. Exhaust the researcher's tool call budget midway through a task — what does the synthesizer do with a partial finding?
2. Return garbage from a tool (inject a mock that returns HTML instead of JSON) — does the agent handle it or hallucinate?
3. Give the planner an ambiguous request — does it ask for clarification or make bad assumptions?
4. Kill the pipeline mid-run — can you resume without losing work?
5. Run a task that requires more context than fits in the researcher's context window — what breaks?

### Lessons learned document

Write up what you found and how you would address each failure mode in a production system. This document is the bridge between this project and Orchid V3 planning.

---

## Deliverables checklist

- [ ] Working 3-agent pipeline (planner → researcher → synthesizer)
- [ ] GitHub MCP and web search MCP wired up and tested
- [ ] Typed handoff schemas between all agents
- [ ] Tool error handling for all failure classes
- [ ] Loop prevention with escape conditions
- [ ] Resumable pipeline state
- [ ] Failure mode documentation from deliberate experiments
- [ ] Lessons learned doc for Orchid V3

---

## Where to start right now

Get a single Researcher agent working with one MCP tool — web search is easiest. Give it a task, let it call the tool, and get a structured finding back. Don't build the Planner or Synthesizer yet. Once the Researcher is solid — especially its error handling and escape conditions — the other two agents are mostly prompt engineering and schema design on top of the same foundation.
