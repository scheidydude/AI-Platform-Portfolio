# Lessons Learned — P06 Integration

**Project:** P06 — Secure Agentic Pipeline  
**Date:** 2026-06-06  
**Scope:** What the P05 unit tests didn't catch, interface design observations, and the path to applying these controls in P02's gateway layer.

---

## 1. What Unit Tests Didn't Catch

### 1a. The `src` namespace collision

P05's 55 unit tests all import from `src.content_isolation` and `src.pii_scanner` — the `src` namespace that hatchling exposes when P05 is installed. P03 also exposes a `src` namespace.

When both are editable-installed in the same virtual environment, their `.pth` files both add project roots to `sys.path`. Whichever `src/__init__.py` Python finds first wins. P05's tests never discovered this because they run in P05's own isolated venv where only P05's `src` exists.

**Fix required:** Rename P06's source directory from `src/` to `p06/` to avoid shadowing either parent's namespace. This was a 5-minute change but required understanding the hatchling + editable install + `sys.path` interaction.

**Lesson:** Namespace collision between co-installed packages only surfaces when packages are composed. Isolated venv tests guarantee nothing about composition behavior.

### 1b. `Path('.').parent.resolve()` does not give the parent directory

`Path('.').parent` returns the relative path `'.'` (a no-op on `.`), not `'..'`. Calling `.resolve()` on `'.'` gives the CWD, not its parent. The correct form is `Path(__file__).resolve().parent`.

P05's tests never exercise path resolution because P05 has no cross-project path dependencies. P06 is the first project in the portfolio that needs to locate sibling directories at runtime.

**Lesson:** Relative path resolution in editable packages requires `__file__`-anchored paths, not CWD-anchored paths.

### 1c. `file://../relative` is rejected by pip

P05 and P03 each have a pyproject.toml. The natural assumption was that P06 could declare them as path dependencies using the PEP 508 direct URL syntax: `"project-03 @ file://../project-03"`. This fails: pip rejects non-absolute `file://` URIs on POSIX systems.

**Fix required:** Use `uv pip install -e ../project-03-agentic-mcp` directly, bypassing pip's URL validation. Documented in `pyproject.toml` as a `[tool.uv.sources]` entry for tooling awareness even though uv's project-install path (`uv sync`) is not used.

**Lesson:** pip's path dep URL handling is stricter than expected. uv handles relative paths correctly in its own toolchain but not when delegating to pip.

### 1d. hatchling rejects `packages = []`

P06's hatchling build config originally used `packages = ["src"]`, then `packages = []` (after the namespace rename decision). Hatchling requires at least one package to be declared; an empty list fails validation.

**Fix required:** Remove `[build-system]` from P06's `pyproject.toml` entirely. P06 is an integration layer, not a library. It does not need to be installable as a package — only its dependencies need installing.

**Lesson:** A `pyproject.toml` without `[build-system]` is valid for projects that are never published as packages. Removing the build backend entirely is the correct choice for integration/test-only projects.

---

## 2. P05 Interface Design: What Made Integration Easy or Hard

### Easy

**`scan_output_for_pii()` takes a plain string.** No wrapper type, no class instantiation, no configuration required. `finding.content` passed directly. Zero adaptation needed at Wiring Point 2. This is the right interface design for a security scanner — it should accept the most common representation of text output.

**`_reset_analyzer()` for test isolation.** P05's test suite exposes `_reset_analyzer()` to reset the Presidio singleton. This made P06's mock strategy identical to P05's — no novel mock infrastructure needed.

**`preprocess_content()` and `isolate_chunk()` are individually callable.** Even though `prepare_retrieved_context()` is the high-level entry point, the lower-level functions are public and individually testable. This allowed the preprocessing tests in `test_injection_defense.py` to be granular.

### Hard

**`prepare_retrieved_context()` takes `list[RetrievedChunk]`, not `str`.** P05 was designed for a batch-retrieval model (fetch chunks, then inject into context once). P03 uses a streaming tool-call model (each tool result becomes a message turn as the conversation proceeds). The two approaches are architecturally incompatible at the interface level.

This mismatch is the central architectural finding of P06. The adapter `_to_retrieved_chunk()` bridges the gap for testing but not for live wiring inside the agentic loop. Wiring Point 1 cannot be live-wired without modifying P03's `ResearcherAgent.run()` to call `prepare_retrieved_context()` before appending tool results to the messages list.

**`RetrievedChunk` is a frozen dataclass, not a Pydantic model.** P03 uses Pydantic throughout (`ResearchFinding`, `ResearchTask`, `PipelineState`). Mixing frozen dataclasses and Pydantic models in the same data flow requires explicit conversion — there is no automatic coercion. In a production codebase, standardizing on one serialization strategy across both projects would eliminate this friction.

**Presidio requires a heavy install (`en_core_web_lg` is ~750 MB).** For a portfolio project this is acceptable. For a production gateway, the NLP model loading time (~2–5 seconds on cold start) and memory footprint (~500 MB) would require a separate sidecar service rather than an in-process library call.

---

## 3. Applying Controls to P02's Gateway Layer

P02 implements an LLM gateway (`POST /v1/chat/completions`). The same two controls apply to the gateway layer but at different integration points.

### Output PII Scan (Wiring Point 2 in gateway context)

**Location:** Gateway response handler — after the upstream LLM returns, before the response is forwarded to the client.

```python
# In gateway response path:
from pii_scanner import scan_output_for_pii

response_text = llm_response["choices"][0]["message"]["content"]
result = scan_output_for_pii(response_text)

if result.action == "block":
    return JSONResponse(
        status_code=422,
        content={"error": BLOCK_RESPONSE_TEXT},
        headers={"X-PII-Block": "true"},
    )
if result.action == "warn":
    # Forward response but add warning header
    response.headers[PII_WARNING_HEADER] = ",".join(result.entity_types_found)
```

**Differences from P06 wiring:**
- The gateway operates on HTTP responses, not Python objects — `scan_output_for_pii` still takes a plain `str`, so the integration contract is identical.
- The error response is an HTTP 422, not a Python exception.
- Streaming responses require buffering before scanning (the scanner cannot operate on partial tokens).

### Content Isolation (Wiring Point 1 in gateway context)

**Location:** Gateway request pre-processing — the system prompt and any retrieval context injected by the gateway before forwarding to the LLM.

**Approach:** The hardened system prompt (`prompts/system_prompt_hardened.md` from P05) already instructs the model to treat retrieved content as lowest-trust data. For per-request content isolation, the gateway would:
1. Intercept any `[CONTEXT]` blocks in the system prompt or user message
2. Apply `prepare_retrieved_context()` to content fetched from Confluence/Jira before injection
3. Return the modified request to the LLM

**Key difference from P06:** The gateway's retrieval model is explicit (gateway fetches content and injects it) rather than streaming (P03's model fetches content incrementally via MCP tool calls). This means `prepare_retrieved_context()` can be applied before the LLM request is dispatched — no agentic loop hook is needed. The gateway context is actually the architecture that P05's interface was designed for.

### What P02 needs from P05 to enable this

1. `pii_scanner.py` and `content_isolation.py` must be importable in the gateway's Python environment — same sys.path injection approach as P06, or a proper packaging step for P05.
2. Presidio's spaCy model must be available. For a gateway service, this means including `en_core_web_lg` in the Docker image or running a Presidio sidecar.
3. The `BLOCK_RESPONSE_TEXT` and `PII_WARNING_HEADER` constants from `pii_scanner.py` should be used verbatim to maintain consistent user-facing messaging across both the gateway and pipeline layers.
