# HANDOFF — Project 03: Agentic Systems & MCP

**Written:** 2026-05-23  
**Repo:** `/Users/david/Development/scheidydudes-github-repos/ai-path-learning/project-03-agentic-mcp`  
**HEAD:** `2bfd2a7`

---

## 1. Mission

Building a 3-agent research pipeline (Planner → Researcher → Synthesizer) wired to real MCP servers, as a deliberate stress-test of multi-agent failure modes. The goal is equal parts functional PoC and career documentation — every architectural decision gets an ADR, every phase gets documented. This feeds into Orchid V3 design. Success = working pipeline + complete docs portfolio.

---

## 2. Current State

### Working and verified (commit `2bfd2a7`)

- **SearXNG MCP server** (`src/mcp_servers/searxng_server.py`): `web_search` + `fetch_page`. Verified: hits `https://search.scheidy.com/search?q=...&format=json`, returns structured results. Tested in 4 live runs.
- **GitHub MCP server** (`src/mcp_servers/github_server.py`): `search_repositories`, `get_file_contents`, `search_code`. Verified: hits GitHub REST API with PAT from `.env`. `search_code` correctly blocks without a token.
- **MultiServerClient** (`src/tools/multi_server.py`): spawns both MCP servers as stdio subprocesses simultaneously via `AsyncExitStack`. Tool aggregation and call routing by tool name both work. Verified: 5 tools visible across 2 servers in a single session.
- **Researcher agent** (`src/agents/researcher.py`): end-to-end working. Tool call budget enforcement, duplicate call detection (by `(tool_name, args_hash)`), partial-return on budget exhaust, wall-time enforcement, XML tag stripping on final output. Verified: `confidence=high`, 4–6 tool calls, live sources in 3 separate test runs.
- **ToolResult wrapper** (`src/tools/wrapper.py`): catches all 5 error classes (rate_limit/429, not_found/404, timeout, bad_output, unavailable). Also checks MCP protocol-level `isError` flag on call results. No raw exceptions reach agent context.
- **All Pydantic schemas** (`src/models.py`): `ResearchTask`, `ResearchFinding`, `AgentConstraints`, `PipelineState`, `ToolResult`, `Source`.
- **Docs**: SRS, system design, ADR-000 through ADR-006, running index. All in `docs/`.

### Half-built / in what state

- **Phase 2 task_plan.md** still shows `in_progress` with unchecked boxes — but Phase 2 is functionally complete. First action: update `task_plan.md` to mark Phase 2 `complete`.
- **`docs/design/handoff-schemas.md`**, `tool-error-handling.md`, `loop-prevention.md` — listed in `docs/index.md` as `not_started`. These are documentation gaps, not code gaps.
- **`findings.md`** — has placeholder tables, not populated with actual findings from the builds this session. Low priority.

### Not built yet

- **Planner agent** — no code exists
- **Synthesizer agent** — no code exists  
- **Orchestrator** — no code exists; `PipelineState` schema exists in `src/models.py` but is never used
- **State persistence** — `PipelineState` is never written to disk; `state/` only has `ResearchFinding` JSON from test runs
- **Tests** — zero tests written, deliberate for PoC phase

### Exact next action

Update `task_plan.md` Phase 2 status to `complete`, then begin Phase 3: loop prevention hardening. Specifically — **progress stall detection is the only missing loop-prevention piece** (the other two are already partially in place; see Gotchas).

---

## 3. Decisions Made (and Why)

**Decision:** Python, no framework abstraction  
**Alternatives:** TypeScript, LangChain/LangGraph  
**Reason:** Best MCP SDK support, Pydantic native, LangChain explicitly rejected because it would hide the failure modes this project is designed to surface  
**Reversibility:** Load-bearing for the PoC; not worth changing

---

**Decision:** `mcp` Python SDK directly (stdio subprocess per server)  
**Alternatives:** Anthropic SDK tool_use layer, `langchain-mcp`  
**Reason:** Direct protocol access forces explicit error handling — the point of the project  
**Reversibility:** Low — `MultiServerClient` is built around this

---

**Decision:** Self-hosted SearXNG at `https://search.scheidy.com/` as web search MCP  
**Alternatives:** Brave Search, Tavily  
**Reason:** No API cost, no rate-limit risk during Phase 5 experiments, full control  
**Reversibility:** Easy to swap — just change the `SEARXNG_BASE` constant in `searxng_server.py`

---

**Decision:** Custom Python GitHub MCP server (not npm package)  
**Alternatives:** `@modelcontextprotocol/server-github` (npm), `github-mcp-server` (Go binary)  
**Reason:** The npm package is deprecated (`Package no longer supported` warning), Go binary not installed. Writing custom Python server is consistent with SearXNG approach and produces a portfolio artifact.  
**Reversibility:** Easy to swap if official Python SDK-based server appears

---

**Decision:** JSON to disk for state persistence, atomic write via `os.replace()`  
**Alternatives:** SQLite, Redis  
**Reason:** Zero deps, human-readable during debugging, Pydantic serializes natively  
**Reversibility:** Only `PipelineState` uses this — easy to swap when Orchestrator is built

---

**Decision:** Sequential orchestration; streaming evaluation deferred to Phase 4  
**Alternatives:** Streaming (incremental synthesizer), parallel researcher tasks  
**Reason:** Simpler resume logic, easier to observe failure modes  
**Reversibility:** Phase 4 explicitly revisits this

---

**Decision:** Self-hosted Qwen3-35B via llama.cpp at `http://ai.scheidy.com:8082` as LLM  
**Alternatives:** Anthropic Claude API (original plan)  
**Reason:** No external API key available in environment; user has a homelab llama.cpp server already running. Using `openai.AsyncOpenAI` with custom `base_url` — no Anthropic SDK in the project.  
**Reversibility:** Easy — swap `LLM_BASE_URL` and `MODEL` in `researcher.py`, add `anthropic` package, adapt message format (different tool schema: `input_schema` vs `parameters`, different tool result format)

---

## 4. Architecture & Key Files

```
src/
├── models.py                    # All Pydantic schemas. Never import from here into MCP servers (subprocess isolation).
├── mcp_servers/
│   ├── searxng_server.py        # Standalone MCP server — runs as stdio subprocess. Hits search.scheidy.com.
│   └── github_server.py        # Standalone MCP server — runs as stdio subprocess. Hits api.github.com. Reads GITHUB_TOKEN from env.
├── tools/
│   ├── wrapper.py               # call_tool_safe(): catches all exceptions + MCP isError, returns ToolResult always.
│   │                            # Also: mcp_tools_to_openai(), _classify_mcp_error()
│   └── multi_server.py          # MultiServerClient: AsyncExitStack-based, spawns N servers, aggregates tools, routes by name.
└── agents/
    └── researcher.py            # ResearcherAgent.run(task) → ResearchFinding. Uses MultiServerClient + AsyncOpenAI.
                                 # Contains: budget enforcement, loop detection, XML tag stripping, forced-summary recovery.

main.py                          # Test harness. Loads .env FIRST (before src imports). Runs one Researcher task.
docs/
├── index.md                     # KEEP UPDATED. Running index of all artifacts. Check this to know what doc state is.
├── SRS.md                       # Full requirements spec.
├── design/system-design.md      # Architecture overview + all data model schemas (source of truth for schema design).
└── ADR/ADR-001 through ADR-006  # All accepted. Do not re-debate these.
task_plan.md                     # Phase tracker. Currently stale — Phase 2 shows in_progress but is complete.
state/                           # Gitignored. Runtime output (ResearchFinding JSON files from test runs).
.env                             # Gitignored. Has GITHUB_TOKEN. DO NOT COMMIT.
```

**Files that look touchable but shouldn't be:**
- `src/models.py` — schemas are stable; downstream code depends on the exact field names
- Any file in `docs/ADR/` — decisions are accepted and documented

---

## 5. Gotchas & Hard-Won Knowledge

**Qwen3 on llama.cpp emits XML tool calls in response text.** When the model reaches `finish_reason="stop"` but still wanted to call a tool, it sometimes emits `<tool_call><function=...>...</tool_call>` XML in the response content instead of using the OpenAI `tool_calls` API. This happens on both normal stop AND on the wrap-up call after budget exhaustion. Mitigation: `_strip_tool_call_tags()` applied to all final text; if content is empty after stripping, a second "please just write text" call is made. This costs an extra LLM round-trip but produces clean output.

**MCP tool errors don't raise Python exceptions on the client.** If the tool function inside an MCP server raises an exception, the MCP protocol catches it and returns a `CallToolResult` with `isError=True`. The client's `session.call_tool()` does NOT raise — it returns normally. Without checking `result.isError`, you'll treat errors as successful tool calls with error text as data. `call_tool_safe()` now checks this explicitly.

**`hatchling` won't auto-detect the package.** The project uses `src/` layout. Hatchling requires explicit `[tool.hatch.build.targets.wheel] packages = ["src"]` in `pyproject.toml`. Without it, `uv pip install -e .` fails with "Unable to determine which files to ship."

**`load_dotenv()` must run before any `src` imports.** `github_server.py` reads `GITHUB_TOKEN` from `os.environ` at call time (inside `_headers()`), so timing doesn't matter there. But anything that reads env at import time would miss it. Keep the `load_dotenv()` call at the very top of `main.py` before the `src` imports.

**`@modelcontextprotocol/server-github` npm package is deprecated** as of 2025-04-08 with "Package no longer supported." Don't use it. The custom `github_server.py` is the replacement.

**The npm-based MCP server approach doesn't mix well with Python.** The official GitHub MCP server is now a Go binary (`github-mcp-server`). It's not installed on this machine. If the user installs it later, the `MultiServerClient` can use it via `StdioServerParameters(command="github-mcp-server", args=["stdio"])` with `env={"GITHUB_TOKEN": ...}`.

**Loop detection in the Researcher is partial.** The `seen_calls` set catches *identical* tool calls (same name + same args). It does NOT catch *progress stall* — where the agent makes N different tool calls but adds no new information to the finding. Progress stall detection (checking if `content` grew between calls) is listed as a Phase 3 requirement but is NOT implemented.

**Circular delegation prevention** is trivially satisfied right now because there's only one agent. It becomes relevant in Phase 4 when Planner and Synthesizer exist. The `PipelineState` schema enforces forward-only status transitions, but there's no runtime check yet.

**The sync Anthropic client doesn't work inside an anyio async context manager.** The original design used `anthropic.Anthropic` (sync). Using it inside `async with stdio_client(...)` causes `ExceptionGroup` wrapping from anyio's TaskGroup. Solution: switched to `openai.AsyncOpenAI` (async) and `await client.chat.completions.create(...)`.

**`search_code` requires a GitHub token.** The GitHub REST API rejects unauthenticated code search. `github_server.py` checks for `GITHUB_TOKEN` and returns a structured error message if missing, rather than propagating a 422 from the API.

---

## 6. Conventions In Play

- **No comments on what code does** — only comments on *why* (hidden constraint, workaround, non-obvious invariant)
- **No tests yet** — deliberate PoC phase; Phase 3 is when tests should start appearing (especially for loop detection and error handling)
- **Every ADR goes in `docs/ADR/`** and gets added to `docs/index.md` immediately. This is a career documentation project — docs are first-class deliverables.
- **Update `progress.md` and `task_plan.md` at the end of each session** before committing
- **Commit style:** `type: short description` with a body that explains what changed conceptually, not line-by-line. See commit `2bfd2a7` for the pattern.
- **`ToolResult` is the error boundary** — nothing below `call_tool_safe()` leaks exceptions upward
- **MCP servers are pure subprocess scripts** — they import nothing from `src/` (no shared models). They're standalone. This is intentional: subprocess isolation means they can't break the agent process.
- **State files go in `state/`** (gitignored). They're runtime artifacts, not source.
- **Caveman mode is active** in this session — terse responses, no fluff. The user has this configured as a startup hook.

---

## 7. Open Questions

1. **Should progress stall detection compare full content or just length?** The spec says "if no new information has been added to the finding" — but the researcher doesn't accumulate a `finding.content` string during execution, only at the end. Need to decide whether to track intermediate content or use a simpler heuristic (e.g., no new sources added in last N calls).

2. **Planner agent: how opinionated should the decomposition be?** The spec says "decompose into a structured research plan with discrete tasks." Should the planner be allowed to ask the user for clarification on ambiguous requests (one of the Phase 5 experiments), or should it always make a best-guess decomposition and flag low-confidence tasks?

3. **Synthesizer output format**: the spec says "structured report with citations." Does the user want this as a Pydantic model (machine-readable) or as markdown prose (human-readable)? This affects how the Synthesizer is prompted.

4. **`handoff-schemas.md` and `tool-error-handling.md`**: listed in `docs/index.md` as `not_started`. These are design docs that should be written before Phase 3 and Phase 4 respectively. Should these be written before coding, or derived from the code after it's built?

5. **GitHub PAT scope**: the PAT in `.env` — what scopes does it have? `search_code` needs at minimum `public_repo` read. `get_file_contents` on private repos needs `repo`. This matters if Phase 5 experiments target private repos.

---

## 8. Do Not Touch

- **`docs/ADR/ADR-001` through `ADR-006`** — all accepted. Do not re-debate language, MCP SDK, SearXNG, JSON persistence, sequential orchestration, or the llama.cpp backend unless the user explicitly opens the question.
- **`src/models.py` schema field names** — downstream code binds to these. Renaming fields breaks serialized state files in `state/`.
- **`src/tools/wrapper.py` `ToolResult` interface** — the Researcher agent depends on `result.success`, `result.data`, `result.error_class`. Don't add or remove fields without updating all callsites.
- **`.env`** — has the real GitHub PAT. Never commit it (it's in `.gitignore`). Never log it.
- **The stdio subprocess architecture for MCP servers** — `MultiServerClient` uses `AsyncExitStack` to manage subprocess lifetimes. This is deliberately low-level. Don't abstract it further unless a concrete problem demands it.
- **`/no_think` prefix in `SYSTEM_PROMPT`** — this disables Qwen3's extended reasoning mode. Removing it causes significantly slower, more verbose responses that often don't improve quality for tool-calling tasks.

---

## 9. Resume Command

> Read `HANDOFF.md` and `task_plan.md`. The first action is to mark Phase 2 complete in `task_plan.md`, then begin Phase 3 (loop prevention). The specific gap: **progress stall detection** is not implemented — the researcher has duplicate-call detection but no check for whether new information is being added across calls. Before implementing, write `docs/design/loop-prevention.md` documenting the design, then code it. Do not re-debate any decision in `docs/ADR/`. Do not touch `src/models.py` schema field names. Confirm the loop-prevention design doc before writing code.
