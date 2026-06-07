# Progress Log — Project 03: Agentic Systems & MCP

**Started:** 2026-05-23

---

## Session Log

### 2026-05-23 — Session 1

**Status:** Planning initialized  
**Phase:** Pre-work  
**Done:**
- Read project spec (`project-03-agentic-mcp.md`)
- Created `task_plan.md`, `findings.md`, `progress.md`

---

### 2026-05-23 — Session 2

**Status:** Phase 1 complete, Phase 2 in progress — Researcher agent working end-to-end  
**Phases:** 1 (complete), 2 (in progress)

**Done:**
- All ADRs accepted (ADR-001 through ADR-005) + ADR-006 (LLM backend)
- SRS written (`docs/SRS.md`)
- System design doc written (`docs/design/system-design.md`)
- Full doc index created (`docs/index.md`)
- Project structure created: `src/models.py`, `src/mcp_servers/`, `src/tools/`, `src/agents/`
- Custom SearXNG MCP server written (`src/mcp_servers/searxng_server.py`) — no pre-built package existed
- `ToolResult` wrapper + error handling written (`src/tools/wrapper.py`)
- Researcher agent written (`src/agents/researcher.py`)
- **End-to-end validated**: Researcher ran against real query, made 4 tool calls via SearXNG MCP, returned `confidence=high` finding with 4 sources
- ADR-006 added mid-session: switched from Anthropic SDK to OpenAI SDK targeting self-hosted Qwen3-35B llama.cpp server (`http://ai.scheidy.com:8082`)

**Issues encountered:**
- `hatchling` build error: needed `[tool.hatch.build.targets.wheel] packages = ["src"]` in pyproject.toml
- Anthropic SDK (sync client) incompatible inside anyio async context manager → switched to `openai.AsyncOpenAI`
- `ANTHROPIC_API_KEY` not in environment → replaced with self-hosted llama.cpp (ADR-006)

**Blockers:** None

---

### 2026-05-23 — Session 3: Phase 2 (complete) + Phase 3

**Status:** Phases 2 and 3 complete  

**Done:**

**Phase 2 remaining — GitHub MCP:**
- `src/mcp_servers/github_server.py` — custom Python MCP server wrapping GitHub REST API; tools: `search_repositories`, `get_file_contents`, `search_code`
- `src/tools/multi_server.py` — `MultiServerClient` spawns SearXNG + GitHub MCP servers simultaneously as stdio subprocesses via `AsyncExitStack`
- `ToolResult` wrapper: all 5 failure classes handled — 429 (exp backoff + jitter, max 3 retries), 404 (low confidence, continue), timeout (log + mark unavailable), bad output (validate schema, reformat once, skip), unavailable (fail gracefully, inform synthesizer)

**Phase 3 — Loop Prevention:**
- `src/agents/researcher.py` updated with all 3 loop prevention mechanisms:
  - Infinite retry guard: tracks `(tool_name, args_hash)` per task; escalates on duplicate
  - Progress stall detection: progress check every N calls; escape if no new content
  - `AgentConstraints(max_tool_calls, max_iterations, max_wall_time_seconds, on_exceed)` — `on_exceed="return_partial"` on every agent
- Wrote `docs/design/loop-prevention.md`

**Blockers:** None

---

### 2026-05-23 — Session 4: Phase 4 — Orchestration

**Status:** Phase 4 complete

**Done:**
- `src/agents/planner.py` — `PlannerAgent.run(topic)` → `list[ResearchTask]`; decomposes user query into discrete research tasks with typed `success_criteria`
- `src/agents/synthesizer.py` — `SynthesizerAgent.run(topic, plan, findings)` → structured report from `dict[str, ResearchFinding]`; flags partial findings in prompt
- `src/orchestrator.py` — `Orchestrator.run(topic, pipeline_id?)`:
  - Sequential: Planner → Researcher (per task) → Synthesizer
  - `PipelineState` persisted to disk via atomic `os.replace(tmp, path)` after every transition
  - Resume: pass existing `pipeline_id` → loads state JSON, skips completed tasks
  - State transitions: `planning → researching → synthesizing → complete`
- `docs/design/orchestration.md` written
- End-to-end pipeline validated: multiple `state/finding_*.json` artifacts written

**Blockers:** None

---

### 2026-05-23 — Session 5: Phase 5 — Failure Mode Experiments

**Status:** Phase 5 complete — project complete

**Done:**
- All 5 failure-mode experiment scripts implemented in `experiments/`:
  - `exp1_budget_exhaustion.py` — `max_tool_calls=1` on multi-criterion task; confirms `partial=True`, `confidence="low"`, gaps populated
  - `exp2_garbage_tool_output.py` — patches `call_tool_safe` to return HTML; verifies `ToolResult` validation path and graceful handling
  - `exp3_ambiguous_planner.py` — underspecified topic input; documents planner assumption behavior
  - `exp4_resume.py` — mid-run kill + resume; **verified**: `state/exp4_d7fa13.json` exists as evidence of completed partial state, pipeline resumed without re-running completed tasks
  - `exp5_context_overflow.py` — task designed to exceed researcher context window; documents truncation and partial finding behavior
- `docs/lessons_learned.md` — production mitigations for each failure mode (Orchid V3 design notes)

**Key findings from experiments:**
- `partial_reason` field missing from `ResearchFinding` — synthesizer can't distinguish "budget exhausted" from "inherently uncertain" (mitigation: add `Literal["budget", "time", "stall", None]` field)
- Resume works correctly: exp4 state file confirms tasks already in `findings` dict are skipped by orchestrator
- Garbage tool output is handled at `ToolResult` level before it reaches the LLM context

**Blockers:** None

---

## Test Results

| Test | Date | Result | Notes |
|------|------|--------|-------|
| SearXNG endpoint reachability | 2026-05-23 | PASS | 17 results returned for "test" query |
| Researcher agent end-to-end | 2026-05-23 | PASS | confidence=high, 4 tool calls, 4 sources, `state/finding_af248f08.json` |
| Full 3-agent pipeline | 2026-05-23 | PASS | Multiple `state/finding_*.json` artifacts; orchestrator state transitions verified |
| Exp 4 mid-run kill + resume | 2026-05-23 | PASS | `state/exp4_d7fa13.json` — partial state written; resume skipped completed tasks |

---

## Files Created / Modified

| File | Action | Session |
|------|--------|---------|
| `task_plan.md` | created | 2026-05-23 |
| `findings.md` | created | 2026-05-23 |
| `progress.md` | created | 2026-05-23 |
| `docs/index.md` | created | 2026-05-23 |
| `docs/SRS.md` | created | 2026-05-23 |
| `docs/design/system-design.md` | created | 2026-05-23 |
| `docs/ADR/ADR-000-template.md` | created | 2026-05-23 |
| `docs/ADR/ADR-001-language-and-framework.md` | created + accepted | 2026-05-23 |
| `docs/ADR/ADR-002-mcp-client-library.md` | created + accepted | 2026-05-23 |
| `docs/ADR/ADR-003-web-search-provider.md` | created + accepted | 2026-05-23 |
| `docs/ADR/ADR-004-state-persistence.md` | created + accepted | 2026-05-23 |
| `docs/ADR/ADR-005-orchestration-pattern.md` | created + accepted | 2026-05-23 |
| `docs/ADR/ADR-006-llm-backend.md` | created + accepted | 2026-05-23 |
| `pyproject.toml` | created | 2026-05-23 |
| `src/models.py` | created | 2026-05-23 |
| `src/mcp_servers/searxng_server.py` | created | 2026-05-23 |
| `src/tools/wrapper.py` | created | 2026-05-23 |
| `src/agents/researcher.py` | created | 2026-05-23 |
| `main.py` | created | 2026-05-23 |
| `state/finding_af248f08.json` | created (test output) | 2026-05-23 |
