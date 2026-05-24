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

**Next:** 
- Wire GitHub MCP server (Phase 2 remaining task)
- Write `docs/design/handoff-schemas.md`
- Begin Phase 3: loop prevention hardening + tests

**Blockers:** None

---

## Test Results

| Test | Date | Result | Notes |
|------|------|--------|-------|
| SearXNG endpoint reachability | 2026-05-23 | PASS | 17 results returned for "test" query |
| Researcher agent end-to-end | 2026-05-23 | PASS | confidence=high, 4 tool calls, 4 sources, `state/finding_af248f08.json` |

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
