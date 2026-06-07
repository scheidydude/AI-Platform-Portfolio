# P06 Findings

## P03 Interface — Wiring Points

### Wiring Point 1: Retrieved content → LLM context (researcher.py)

File: `../project-03-agentic-mcp/src/agents/researcher.py`

No `format_chunks()` function exists (spec pseudocode was illustrative). Content assembled inline around line 176. Exact insertion point TBD on closer read of `ResearcherAgent.run()`. The wrapper must intercept *after* chunks are retrieved but *before* they are injected into the LLM prompt string.

`prepare_retrieved_context()` expects: `list[RetrievedChunk]`
- `RetrievedChunk` is a dataclass: `source: str, chunk_id: str, content: str`
- P03 likely uses its own chunk representation — will need a mapping/adapter

### Wiring Point 2: Finding → persist (orchestrator.py)

File: `../project-03-agentic-mcp/src/orchestrator.py`

Lines 59–60:
```python
state = state.model_copy(update={"findings": {**state.findings, task.task_id: finding}})
self._persist(state)
```

`scan_output_for_pii()` expects: plain `str`
- `ResearchFinding.content` is a `str` field — direct access works
- `PIIScanResult.action` values: `"block"`, `"warn"`, `None`

## P05 Interface

### content_isolation.py

- `prepare_retrieved_context(chunks: list[RetrievedChunk]) -> str`
- `RetrievedChunk(source, chunk_id, content)` — dataclass, frozen
- Output: multi-chunk string with `[RETRIEVED FROM: {source} | TRUST: external-internal | ID: {id}]` markers
- No external deps — stdlib only

### pii_scanner.py

- `scan_output_for_pii(text: str, ...) -> PIIScanResult`
- `PIIScanResult.has_pii: bool`
- `PIIScanResult.action: str` — one of `"block"`, `"warn"`, `None`
- `PIIScanResult.findings: list[PIIFinding]`
- `PIIFinding.entity_type: str` — e.g. `"US_SSN"`, `"EMAIL_ADDRESS"`
- Depends on `presidio-analyzer` (spacy `en_core_web_lg` model required)

## P05 Packaging Wrinkle

**Problem:** P05 has no `pyproject.toml`. Uses `requirements.txt` + flat `src/` layout.

**Cannot use:** `"project-05-security-compliance @ file://../project-05-security-compliance"` — no build backend.

**Options:**
1. Add minimal `pyproject.toml` to P05 (not a source file — packaging infra). Cleanest; enables proper pip install.
2. Append `../project-05-security-compliance/src` to `sys.path` in P06's conftest.py. No P05 modification; fragile but works.
3. Add P05 src path in P06's pyproject.toml via `pythonpath` test config. Test-only, doesn't help runtime.

**Recommended:** Option 1 — add minimal `pyproject.toml` to P05. Spec says "do not modify source files" — a pyproject.toml is packaging infrastructure, not source logic. Both P03 and P05 need unique package names to avoid `src` namespace collision:
- P03 already installed as `project-03-agentic-mcp` with `packages = ["src"]` → installs as `src.*`
- P05 needs `packages = ["src"]` with unique name → same collision problem

**Revised plan:** Use `conftest.py` sys.path injection for P05 (Option 2). Keeps both projects untouched. P06 owns the path wiring in its test config.

## P03 ResearcherAgent — Internal Structure

`ResearcherAgent.run(task: ResearchTask) -> ResearchFinding`
- `ResearchTask.task_id: str`
- `ResearchFinding.task_id: str, content: str`
- `ResearcherAgent` is not a simple function — it manages tool calls, LLM conversation, retry logic
- Wrapping via subclass: override `run()`, call `super().run()`, then scan result

The clean subclass pattern for Point 2 (output scanning):
```python
class SecureResearcherAgent(ResearcherAgent):
    async def run(self, task):
        finding = await super().run(task)
        result = scan_output_for_pii(finding.content)
        if result.action == "block":
            raise PIIInFindingError(task.task_id, result.findings)
        return finding
```

Point 1 (input wrapping) is harder via subclass because content assembly is internal. May need to wrap at orchestrator level or monkey-patch the prompt builder.

## Outstanding Questions

- [ ] What does P03 ResearcherAgent use as its retrieved chunk representation? Does it even do retrieval or just web search via MCP?
- [ ] Does P03 have a retrieval step, or is all content from MCP tool calls (search results)?
- [ ] Exact line in researcher.py where context string is assembled for LLM call
