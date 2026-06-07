# P06 Task Plan — Secure Agentic Pipeline Integration

**Goal:** Wire P05 security controls (`content_isolation.py`, `pii_scanner.py`) into P03 agentic pipeline as active middleware. Demonstrate integration via 3 passing tests. Do NOT modify P03 or P05 source files.

**SUT:** Jira/Confluence AI assistant (common thread across portfolio)

---

## Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Recon | `complete` | Audit P03/P05 interfaces, identify wiring points, discover packaging wrinkle |
| 1 — Dependency wiring | `complete` | pyproject.toml, conftest.py path injection, venv, 5/5 smoke tests passing |
| 2 — Integration wrapper | `not_started` | `p06/secure_researcher.py` thin wrapper |
| 3 — Integration tests | `not_started` | 3 test files, all green |
| 4 — Docs | `not_started` | integration-surface.md, lessons-learned.md, update P05 findings.md |

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

## Phase 2 — Integration wrapper

**Tasks:**
- [ ] Create `src/secure_researcher.py` — subclass or wrapper around `ResearcherAgent`
- [ ] Intercept point 1: wrap retrieved chunks with `prepare_retrieved_context()` before LLM
- [ ] Intercept point 2: scan `ResearchFinding.content` with `scan_output_for_pii()` before persist

**Constraint:** No modification to P03 or P05 source files.

---

## Phase 3 — Integration tests

**Tasks:**
- [ ] `tests/test_injection_defense.py` — injection payload wrapped; without-wrapping contrast
- [ ] `tests/test_pii_scan_on_findings.py` — SSN/email blocked; benign passes
- [ ] `tests/test_pipeline_regression.py` — full pipeline, benign topic, controls active, no regression

---

## Phase 4 — Docs

**Tasks:**
- [ ] `docs/integration-surface.md` — wiring points, interface contracts, failure modes
- [ ] Update `../project-05-security-compliance/findings.md` with integration validation
- [ ] `docs/lessons-learned.md` — what unit tests missed, design observations

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

- [ ] `src/secure_researcher.py`
- [ ] `pyproject.toml`
- [ ] `tests/test_injection_defense.py`
- [ ] `tests/test_pii_scan_on_findings.py`
- [ ] `tests/test_pipeline_regression.py`
- [ ] `docs/integration-surface.md`
- [ ] `../project-05-security-compliance/findings.md` updated
- [ ] `docs/lessons-learned.md`
