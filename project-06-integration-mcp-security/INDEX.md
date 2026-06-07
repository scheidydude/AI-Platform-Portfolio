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
| [`tests/test_injection_defense.py`](tests/test_injection_defense.py) | Injection payload wrapped+labeled; contrast without control | Not started |
| [`tests/test_pii_scan_on_findings.py`](tests/test_pii_scan_on_findings.py) | SSN/email blocked on ResearchFinding; benign passes | Not started |
| [`tests/test_pipeline_regression.py`](tests/test_pipeline_regression.py) | Full pipeline, benign topic, controls active, baseline parity | Not started |

---

## Docs (Phase 4)

| Document | Description | Status |
|----------|-------------|--------|
| [`docs/integration-surface.md`](docs/integration-surface.md) | Wiring contracts, failure modes, upgrade guide | Not started |
| [`docs/lessons-learned.md`](docs/lessons-learned.md) | What unit tests missed; interface design critique; P02 extension path | Not started |
| [P05 findings.md](../project-05-security-compliance/findings.md) | Integration validation evidence added to parent project | Not started |

---

## Final Rollup Checklist

- [ ] SRS complete with acceptance criteria
- [ ] DESIGN-001 shows wiring points, sequence diagrams, interface contracts
- [ ] All ADRs written and accepted (ADR-001 through ADR-003)
- [ ] `secure_researcher.py` wraps P03 with zero source modifications
- [ ] 3 test files, all passing: injection defense, PII scan, regression
- [ ] `docs/integration-surface.md` complete
- [ ] P05 `findings.md` updated with integration validation evidence
- [ ] `docs/lessons-learned.md` complete
- [ ] INDEX.md links all artifacts

---

*Last updated: 2026-06-06 — Phase 1 complete (5/5 smoke tests passing). Phase 2 next.*
