# Project 05 — Enterprise AI Security & Compliance: Document Index

**Project:** Formal threat model for an enterprise LLM deployment (Jira/Confluence AI assistant)  
**Goal:** Portfolio-grade artifact + functional PoC  
**Timeline:** 10 days  
**Status:** In Progress

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
| [SRS-001](docs/srs/SRS-001.md) | Software Requirements Specification — AI Security System | Draft |

---

## Design Documents

| Document | Description | Status |
|----------|-------------|--------|
| [DESIGN-001](docs/design/DESIGN-001.md) | System Architecture & Trust Boundary | Draft |

---

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [ADR-001](docs/adr/ADR-001-stride-over-owasp.md) | Use STRIDE instead of OWASP Top 10 for LLM threat modeling | Accepted |
| [ADR-002](docs/adr/ADR-002-trust-hierarchy.md) | Four-tier trust hierarchy for prompt content | Accepted |
| [ADR-003](docs/adr/ADR-003-presidio-pii-scanner.md) | Use Presidio for output PII detection | Accepted |
| [ADR-004](docs/adr/ADR-004-worm-audit-log.md) | S3 Object Lock (WORM) for immutable audit logs | Accepted |
| [ADR-005](docs/adr/ADR-005-tool-layer-permissions.md) | Enforce permissions at tool layer, not model layer | Accepted |

---

## System Definition (Phase 1)

| Document | Description | Status |
|----------|-------------|--------|
| [SYSTEM-DEF-001](docs/system-def/SYSTEM-DEF-001.md) | Component inventory, trust boundaries, data flows, MCP tool catalog, interface catalog | **Complete** |

## Threat Model (Phase 2)

| Document | Description | Status |
|----------|-------------|--------|
| [THREAT-MODEL-001](docs/threat-model/THREAT-MODEL-001.md) | 22 threats across all 6 STRIDE categories; component mapping; residual risk acceptance | **Complete** |

## Guardrails and Controls (Phase 3)

| Document | Description | Status |
|----------|-------------|--------|
| [GUARDRAILS-MATRIX-001](docs/guardrails/GUARDRAILS-MATRIX-001.md) | 22 controls across 5 layers; threat→control cross-ref; full compliance coverage table | **Complete** |
| [system_prompt_hardened.md](prompts/system_prompt_hardened.md) | Hardened system prompt with trust hierarchy, non-disclosure, role stability; 12 jailbreak test cases | **Complete** |

---

## Implementation (PoC)

| Artifact | Description | Status |
|----------|-------------|--------|
| `src/content_isolation.py` | Prompt injection defense via trust markers | Pending |
| `src/pii_scanner.py` | Output PII scanner (Presidio + regex) | Pending |
| `tests/test_content_isolation.py` | Unit tests for content isolation | Pending |
| `tests/test_pii_scanner.py` | Unit tests for PII scanner | Pending |
| `prompts/system_prompt_hardened.md` | System prompt hardening template | Pending |

---

## Compliance Mapping

| Framework | Relevant Controls | Status |
|-----------|-------------------|--------|
| SEC Rule 17a-4(f) | Immutable audit log, access records | Pending |
| FINRA Rule 4511 | Communication retention, 3–6 year policy | Pending |
| SOC 2 Type II | CC6.1 access controls, CC6.6 untrusted parties, A1.2 availability | Pending |

---

## Final Rollup Checklist

- [x] System definition complete (SYSTEM-DEF-001: 16 components, 7 data flows, 5 tools, 6 classifications)
- [x] All Phase 1 ADRs written and accepted (ADR-001 through ADR-005)
- [x] SRS complete with acceptance criteria (FR-1 through FR-6)
- [x] DESIGN-001 includes full system boundary diagram and attack path walkthroughs
- [x] STRIDE threat model covers all 6 categories (THREAT-MODEL-001: 22 threats, 15 High/Critical pre-control, 3 residual Medium)
- [x] Guardrails matrix complete (GUARDRAILS-MATRIX-001: 22 controls, all threats mapped, no compliance gaps)
- [ ] Two working control implementations with passing tests
- [x] System prompt hardening template complete (12 jailbreak test cases defined)
- [ ] Compliance mapping complete for all 3 frameworks
- [ ] INDEX.md links all artifacts

---

*Last updated: 2026-05-23*
