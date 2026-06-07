# Integration Surface Reference

**Project:** P06 — Secure Agentic Pipeline  
**Audience:** Engineer updating P03 or P05 and needing to know what will break in P06  
**Last updated:** 2026-06-06  
**Related:** [DESIGN-001](design/DESIGN-001.md), [ADR-001](adr/ADR-001-p05-import-strategy.md), [ADR-002](adr/ADR-002-integration-pattern.md)

---

## Overview

P06 owns two wiring points. If either P03 or P05 changes, this document tells you exactly what to check.

```
P03 ResearcherAgent.run()     →  SecureResearcherAgent.run()  →  scan_output_for_pii()   (Point 2)
P05 content_isolation.py      ←  _to_retrieved_chunk()        ←  test_injection_defense  (Point 1, tested)
```

---

## Wiring Point 1 — Content Isolation

### What it does

`prepare_retrieved_context(chunks: list[RetrievedChunk]) -> str` takes external content and wraps it with trust boundary markers before it enters the LLM context. This prevents prompt injection payloads in retrieved content from being indistinguishable from system instructions.

### Contract

**Input:** `list[RetrievedChunk]` where each chunk has:
- `source: str` — origin identifier, e.g. `"mcp/web_search"`. Must not contain `[`, `]`, `|`, newlines, or tabs (stripped by `_UNSAFE_IN_MARKER` regex in `content_isolation.py`).
- `chunk_id: str` — stable identifier. Same constraints as `source`.
- `content: str` — raw retrieved text. May contain any Unicode; unsafe characters are stripped by `preprocess_content()`.

**Output guarantee:** A string where each chunk's content is:
1. Preprocessed (zero-width Unicode, hidden HTML, null bytes removed — CTRL-07)
2. Bounded by `[RETRIEVED FROM: {source} | TRUST: external-internal | ID: {chunk_id}]` ... `[END RETRIEVED CONTENT]` markers (CTRL-01)
3. Any pre-existing marker-like text in `content` is stripped (prevents marker injection attacks)

**P06 type adapter:** `_to_retrieved_chunk(tool_name, tool_call_id, content)` maps P03's MCP tool call fields to `RetrievedChunk`:
```python
RetrievedChunk(
    source=f"mcp/{tool_name}",   # "mcp/web_search", "mcp/fetch_page", etc.
    chunk_id=tool_call_id,        # OpenAI tool_call.id, e.g. "call_abc123"
    content=content,              # str(result.data) from P03
)
```

### What can break

| P03 change | Impact | Fix |
|------------|--------|-----|
| New tool name added to `SEARXNG_SERVER` or `GITHUB_SERVER` | None — `mcp/{tool_name}` adapts automatically | None |
| `tool_call.id` format changes | None — chunk_id is opaque | None |
| Tool result format changes from `str` to structured type | `_to_retrieved_chunk` receives non-string `content` | Update `_to_retrieved_chunk` to extract text from new structure |

| P05 change | Impact | Fix |
|------------|--------|-----|
| `RetrievedChunk` field names change | `_to_retrieved_chunk` construction breaks | Update field names in `_to_retrieved_chunk` |
| `prepare_retrieved_context` signature changes | All callers break | Update P06 call sites |
| Marker format changes (`[RETRIEVED FROM:` prefix) | `test_injection_defense.py` assertions fail | Update marker string assertions in tests |
| `preprocess_content` removed or renamed | Import in `secure_researcher.py` breaks | Update import |

### Live wiring status

**Not live-wired.** Point 1 is verified via direct function testing in `test_injection_defense.py`. The live wiring (applying isolation to tool results inside `ResearcherAgent.run()`) requires an overridable hook that does not exist in P03's current architecture. See ADR-002 and `docs/lessons-learned.md` for the production path forward.

---

## Wiring Point 2 — PII Scan Before Persistence

### What it does

`scan_output_for_pii(text: str) -> PIIScanResult` scans every `ResearchFinding.content` before the finding is returned from `SecureResearcherAgent.run()`. Because `Orchestrator._persist()` is only called after the researcher returns, a `PIIInFindingError` raised here prevents persistence.

### Contract

**Input:** `text: str` — the full text content of a `ResearchFinding`. No preprocessing required; `scan_output_for_pii` handles any encoding.

**Output:** `PIIScanResult` with:
- `.has_pii: bool`
- `.action: str` — one of `"block"`, `"warn"`, `"clean"` (**not** `None`)
- `.findings: list[PIIFinding]` — each with `.entity_type: str`, `.start: int`, `.end: int`, `.score: float`

**Action→behavior mapping in `SecureResearcherAgent.run()`:**

| action | Behavior |
|--------|----------|
| `"block"` | `PIIInFindingError` raised; finding not returned; pipeline transitions to `"failed"` |
| `"warn"` | Warning logged; finding returned unchanged |
| `"clean"` | Finding returned unchanged |

**Entity type→action mapping (defined in `pii_scanner.py`):**

| Entity type | Action | Detector |
|-------------|--------|----------|
| `US_SSN` | block | Presidio |
| `CREDIT_CARD` | block | Presidio |
| `US_BANK_NUMBER` | block | Presidio |
| `CUSIP` | block | Regex |
| `ISIN` | block | Regex |
| `EMAIL_ADDRESS` | warn | Presidio |
| `PERSON` | warn | Presidio |
| `PHONE_NUMBER` | warn | Presidio |
| `IP_ADDRESS` | warn | Presidio |

**Default confidence threshold:** 0.7 — findings below this score are ignored.

### What can break

| P03 change | Impact | Fix |
|------------|--------|-----|
| `ResearchFinding.content` renamed | `scan_output_for_pii(finding.content)` breaks | Update field access in `SecureResearcherAgent.run()` |
| `ResearcherAgent.run()` signature changes (e.g. adds required arg) | `super().run(task)` breaks at call site | Update `SecureResearcherAgent.run()` signature and `super()` call |
| `ResearchFinding` model becomes non-Pydantic | Type check assumptions in tests break | Update fixture construction |

| P05 change | Impact | Fix |
|------------|--------|-----|
| `scan_output_for_pii` signature changes | Import or call site breaks | Update call in `secure_researcher.py` |
| `PIIScanResult.action` values change (e.g. `None` instead of `"clean"`) | Action routing logic silently breaks | Update `if result.action == "block"/"warn"` conditions; add explicit `"clean"` check |
| New action value added (e.g. `"redact"`) | Falls through without handling | Add explicit branch in `SecureResearcherAgent.run()` |
| `PIIFinding` field names change | `PIIInFindingError` construction and tests break | Update field access |
| Presidio version upgrade changes entity types | Entity type assertions in tests fail | Update test fixtures to match new types |

### Presidio dependency

`scan_output_for_pii` depends on `presidio-analyzer` and `spacy en_core_web_lg`. If Presidio is not installed:
- `_get_analyzer()` raises `ImportError` with a clear message
- This propagates through `scan_output_for_pii` and out of `SecureResearcherAgent.run()`
- **P03 fails fast** — the secure pipeline does not degrade gracefully to skip scanning
- This is intentional: a scanner that silently skips provides a false security guarantee

To install: `pip install "presidio-analyzer[nlp]" && python -m spacy download en_core_web_lg`

---

## Import Wiring

P06 depends on both P03 and P05 being importable. The wiring is:

| Dependency | Import mechanism | Location |
|------------|-----------------|----------|
| P03 `src.*` | uv editable install — `.pth` file in `.venv/site-packages` adds `/project-03-agentic-mcp` to `sys.path` | `pyproject.toml` → `uv pip install -e ../project-03-agentic-mcp` |
| P05 `content_isolation`, `pii_scanner` | `sys.path.insert(0, .../project-05-security-compliance/src)` | `tests/conftest.py` (tests) and `p06/secure_researcher.py` (runtime) |

**Directory layout assumption:** Both P03 and P05 must be at `../project-03-agentic-mcp` and `../project-05-security-compliance` relative to P06. If either project is moved, update:
- `pyproject.toml` `[tool.uv.sources]` path
- `tests/conftest.py` `_P05_SRC` and `_P06_ROOT` paths
- `p06/secure_researcher.py` `_P05_SRC` path

---

## Performance

| Control | Per-call cost | Source |
|---------|--------------|--------|
| `preprocess_content()` | ~5–50 µs | stdlib regex, no I/O |
| `isolate_chunk()` | ~5–20 µs | string concatenation |
| `scan_output_for_pii()` with Presidio | ~50–200 ms | spaCy NER inference |
| `scan_output_for_pii()` regex-only (no Presidio) | ~1–5 ms | regex only |

Typical P03 pipeline runtime per task: 30–300 seconds (dominated by LLM API and web tool calls). PII scan overhead is **< 0.5%** in normal operation.

---

## Verification

To confirm P06 is correctly wired after any change:

```bash
cd project-06-integration-mcp-security
.venv/bin/pytest tests/ -v   # must show 53 passed

# Confirm P03/P05 source files unchanged:
git diff ../project-03-agentic-mcp/src/ ../project-05-security-compliance/src/
# must show no output
```
