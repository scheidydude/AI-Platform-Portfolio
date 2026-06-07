# Project 06 — Secure Agentic Pipeline: Document Index

**Project:** Integration layer wiring P05 security controls into P03 agentic pipeline  
**Goal:** Portfolio-grade artifact + functional PoC demonstrating composed security controls  
**Timeline:** 5 days  
**Status:** In progress — Phase 1

---

## Planning Artifacts

| Document | Purpose | Status |
|----------|---------|--------|
| [task_plan.md](task_plan.md) | Phase tracker, decisions, error log | Active |
| [findings.md](findings.md) | Research, discoveries, technical decisions | Active |
| [progress.md](progress.md) | Session log, test results, reboot check | Active |

---

## Requirements

| Document | Description | Status |
|----------|-------------|--------|
| [SRS-001](docs/srs/SRS-001.md) | Software Requirements Specification — Secure Agentic Pipeline Integration | **Draft** |

---

## Design Documents

| Document | Description | Status |
|----------|-------------|--------|
| [DESIGN-001](docs/design/DESIGN-001.md) | Integration Surface: Wiring Points, Contracts, Sequence Diagrams | **Draft** |

---

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-p05-import-strategy.md) | sys.path injection for P05 (no pyproject.toml in P05) | Accepted |
| [ADR-002](docs/adr/ADR-002-integration-pattern.md) | Subclass pattern for output scanning; isolation applied post-tool-call | Accepted |
| [ADR-003](docs/adr/ADR-003-no-source-modification.md) | Zero modification constraint on P03 and P05 source files | Accepted |

---

## Implementation (PoC)

| Artifact | Description | Status |
|----------|-------------|--------|
| [`pyproject.toml`](pyproject.toml) | P06 metadata; P03 via uv path dep; P05 via conftest sys.path; no build backend (integration layer) | **Complete** |
| [`p06/__init__.py`](p06/__init__.py) | P06 package (uses `p06/` not `src/` to avoid P03 namespace collision) | **Complete** |
| [`p06/secure_researcher.py`](p06/secure_researcher.py) | Thin subclass of ResearcherAgent + SecureOrchestrator wrapper | Not started |
| [`tests/conftest.py`](tests/conftest.py) | sys.path injection: P05 src/ + P06 root; all cross-project imports verified | **Complete** |
| [`tests/test_imports.py`](tests/test_imports.py) | Phase 1 smoke test: 5/5 import verifications passing (delete after Phase 3) | **Complete** |
| [`tests/test_injection_defense.py`](tests/test_injection_defense.py) | 14 tests: adapter, payload wrapped+bounded, contrast, preprocess | **Complete** |
| [`tests/test_pii_scan_on_findings.py`](tests/test_pii_scan_on_findings.py) | 16 tests: SSN/CC blocked, email warn, benign clean, PIIInFindingError | **Complete** |
| [`tests/test_pipeline_regression.py`](tests/test_pipeline_regression.py) | 13 tests: structure, benign path, scan tracking, PII block, baseline parity | **Complete** |

---

## Docs (Phase 4)

| Document | Description | Status |
|----------|-------------|--------|
| [`docs/integration-surface.md`](docs/integration-surface.md) | Wiring contracts, interface contracts, break-surface table, performance, verification | **Complete** |
| [`docs/lessons-learned.md`](docs/lessons-learned.md) | 4 integration bugs unit tests missed; P05 interface critique; P02 gateway wiring path | **Complete** |
| [P05 findings.md](../project-05-security-compliance/findings.md) | Integration validation evidence: both wiring points, 43/43 tests, type compatibility, zero source mod | **Complete** |

---

## Final Rollup Checklist

- [x] SRS complete with acceptance criteria (SRS-001: FR-1, FR-2, FR-3, NFR-1 through NFR-4)
- [x] DESIGN-001 shows wiring points, sequence diagrams, interface contracts
- [x] All ADRs written and accepted (ADR-001 through ADR-003)
- [x] `p06/secure_researcher.py` wraps P03 with zero source modifications (verified: `git diff ../project-03-agentic-mcp/src/` shows nothing)
- [x] 3 test files, all passing: injection defense (14), PII scan (16), regression (13) — 43/43
- [x] `docs/integration-surface.md` complete
- [x] P05 `findings.md` updated with integration validation evidence
- [x] `docs/lessons-learned.md` complete
- [x] INDEX.md links all artifacts

---

*Last updated: 2026-06-06 — **All phases complete. 53/53 tests passing.***
