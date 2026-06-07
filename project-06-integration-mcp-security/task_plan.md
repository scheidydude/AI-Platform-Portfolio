# P06 Task Plan — Secure Agentic Pipeline Integration

**Goal:** Wire P05 security controls (`content_isolation.py`, `pii_scanner.py`) into P03 agentic pipeline as active middleware. Demonstrate integration via 3 passing tests. Do NOT modify P03 or P05 source files.

**SUT:** Jira/Confluence AI assistant (common thread across portfolio)

---

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Recon | `complete` | Audit P03/P05 interfaces, identify wiring points, discover packaging wrinkle |
| 1 — Dependency wiring | `complete` | pyproject.toml, conftest.py path injection, venv, 5/5 smoke tests passing |
| 2 — Integration wrapper | `complete` | `p06/secure_researcher.py` — PIIInFindingError, SecureResearcherAgent, SecureOrchestrator, _to_retrieved_chunk |
| 3 — Integration tests | `complete` | 53/53 passing across 4 test files |
| 4 — Docs | `complete` | integration-surface.md, lessons-learned.md, P05 findings.md updated |

---

## Phase 0 — Recon (complete)

**Key discoveries:**
- P03 wiring point 1: `researcher.py` line ~176 — content assembled before LLM call; no `format_chunks()` exists, content built inline
- P03 wiring point 2: `orchestrator.py` lines 59–60 — `self._persist(state)` after finding stored
- P05 `content_isolation.py` input: `list[RetrievedChunk]` (dataclass with `source`, `chunk_id`, `content`)
- P05 `pii_scanner.py` input: plain `str`; output: `PIIScanResult` with `.has_pii`, `.action`, `.findings`
- **WRINKLE:** P05 has no `pyproject.toml` — can't use path deps as written in spec. See findings.md.
- P03 models: `ResearchFinding` has `.task_id` and `.content` fields (Pydantic BaseModel)
- Both P03 and P05 use `packages = ["src"]` / flat src layout — would conflict if both installed naively

---

## Phase 1 — Dependency wiring (complete)

**Tasks:**
- [x] Create `pyproject.toml` for P06 (P03 via uv path dep; P05 via conftest sys.path)
- [x] Create venv (`uv venv --python 3.11`) and install P03 + pytest
- [x] Rename P06 source dir `src/` → `p06/` (avoids `src` namespace collision with P03)
- [x] Verify P03 `from src.models import ResearchFinding` imports cleanly
- [x] Verify P05 `from content_isolation import ...` imports cleanly
- [x] 5/5 smoke tests passing (`tests/test_imports.py`)

**Errors logged:**
- `file://../project-03-agentic-mcp` doesn't work with pip (non-local URIs) → switched to `uv pip install -e` + `[tool.uv.sources]` then to plain `uv pip install -e ../project-03-agentic-mcp`
- `packages = []` rejected by hatchling → removed `[build-system]` from pyproject.toml (P06 is integration layer, not library)
- `src/` namespace collision with P03 when both editable-installed → renamed P06's source dir to `p06/`
- `Path('.').parent.resolve()` doesn't give parent dir → correct form is `Path(__file__).resolve().parent`

---

## Phase 2 — Integration wrapper (complete)

**Tasks:**
- [x] Create `p06/secure_researcher.py`
- [x] `PIIInFindingError(Exception)` — task_id + pii_findings; descriptive message with entity types
- [x] `SecureResearcherAgent(ResearcherAgent)` — `run()` calls `super().run(task)` then scans finding
- [x] `SecureOrchestrator(Orchestrator)` — `__init__` swaps `self.researcher = SecureResearcherAgent()`
- [x] `_to_retrieved_chunk(tool_name, tool_call_id, content)` — P03→P05 type adapter for Point 1 tests
- [x] P05 path bootstrap at module level (runtime use; conftest.py handles tests)
- [x] All 5 Phase 1 smoke tests still passing

**Constraint:** Zero P03/P05 source modifications — verified.

---

## Phase 3 — Integration tests (complete)

**Tasks:**
- [x] `tests/test_injection_defense.py` — 14 tests: adapter, payload wrapped+bounded, contrast without defense, preprocess strips vectors, multiple chunks
- [x] `tests/test_pii_scan_on_findings.py` — 16 tests: SSN/email/CC blocked, email warn, benign clean, PIIInFindingError raised+shape, scan called with finding.content
- [x] `tests/test_pipeline_regression.py` — 13 tests: structure, benign completes, scan called per finding, state transitions, PII block fails pipeline, finding not persisted, baseline parity
- [x] **53/53 passing** (includes 5 Phase 1 smoke tests)

**Error fixed:** `patch.object(SecureResearcherAgent, "run", wraps=...)` drops `self` on unbound wraps → removed

---

## Phase 4 — Docs (complete)

**Tasks:**
- [x] `docs/integration-surface.md` — per-field break-surface tables for both wiring points, Presidio failure behavior, performance figures, verification commands
- [x] Update `../project-05-security-compliance/findings.md` — integration validation evidence: wiring points exercised, 43/43 test results, type compatibility table, zero source-mod confirmation
- [x] `docs/lessons-learned.md` — 4 bugs unit tests missed (namespace collision, Path resolution, pip URI, hatchling empty packages), P05 interface critique (easy: str input, mock hook, granular functions; hard: batch vs streaming mismatch, frozen dataclass vs Pydantic), P02 gateway wiring with code example

---

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| P05 has no pyproject.toml | Phase 0 recon | sys.path injection via conftest.py (ADR-001) |
| pip rejects `file://../relative` path | Phase 1 attempt 1 | Use `uv pip install -e ../project-03-agentic-mcp` |
| hatchling rejects `packages = []` | Phase 1 attempt 2 | Removed [build-system] entirely; P06 not a library |
| `src` namespace collision P03/P06 | Phase 1 attempt 3 | Renamed P06 source dir to `p06/` |
| `Path('.').parent.resolve()` returns CWD | Phase 1 attempt 4 | Use `Path(__file__).resolve().parent.parent.parent` |

---

## Deliverables Checklist

- [x] `p06/secure_researcher.py` — PIIInFindingError, SecureResearcherAgent, SecureOrchestrator, _to_retrieved_chunk
- [x] `pyproject.toml` — P03 uv path dep; no build backend; P05 via conftest sys.path
- [x] `tests/test_injection_defense.py` — 14 tests passing
- [x] `tests/test_pii_scan_on_findings.py` — 16 tests passing
- [x] `tests/test_pipeline_regression.py` — 13 tests passing
- [x] `docs/integration-surface.md` — wiring contracts, break-surface tables, performance, verification
- [x] `../project-05-security-compliance/findings.md` updated — integration validation evidence
- [x] `docs/lessons-learned.md` — bugs, interface critique, P02 gateway path
- [x] `INDEX.md` — all artifacts linked, final rollup checklist 9/9
- [x] `docs/srs/SRS-001.md` — FR-1, FR-2, FR-3, NFR-1 through NFR-4
- [x] `docs/design/DESIGN-001.md` — architecture, wiring contracts, sequence diagrams
- [x] ADR-001 through ADR-003 — accepted

**Final state:** All phases complete. 53/53 tests passing. Zero P03/P05 source modifications.
