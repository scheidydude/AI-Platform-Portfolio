# Task Plan: Enterprise AI Security & Compliance Threat Model

## Goal
Produce a formal, portfolio-grade threat model for a Jira/Confluence AI assistant using STRIDE, with working control implementations and compliance mappings to SEC 17a-4, FINRA 4511, and SOC 2.

## Current Phase
Phase 4

## Phases

### Phase 1: System Definition
- [x] Define full trust boundary diagram (components, data flows)
- [x] Complete data classification table
- [x] Document system prompt, auth layer, tool layer, logging infra
- **Status:** complete
- **Output:** [SYSTEM-DEF-001](docs/system-def/SYSTEM-DEF-001.md) — 16 components, 6 trust zones, 14-data-asset classification, 5-tool MCP catalog, 3 data flow sequences

### Phase 2: STRIDE Threat Model
- [x] Apply all 6 STRIDE categories to LLM attack surface
- [x] Define scenario, likelihood, impact, and controls per threat
- [x] Document LLM-specific nuances (blurry data/instruction boundary, tool blast radius)
- **Status:** complete
- **Output:** [THREAT-MODEL-001](docs/threat-model/THREAT-MODEL-001.md) — 22 threats; 3 residual Medium risks formally accepted (S-02, I-01, E-03)

### Phase 3: Guardrails Matrix
- [x] Map every threat → control → layer → implementation → compliance ref
- [x] Verify no threat is unmapped
- **Status:** complete
- **Output:** [GUARDRAILS-MATRIX-001](docs/guardrails/GUARDRAILS-MATRIX-001.md) — 22 controls, 22/22 threats mapped, 0 compliance gaps; [system_prompt_hardened.md](prompts/system_prompt_hardened.md) — 12 jailbreak test cases

### Phase 4: Guardrails Implementation
- [ ] Implement content isolation (prompt injection defense)
- [ ] Implement output PII scanner (Presidio or regex)
- [ ] Write system prompt hardening template
- [ ] Verify both controls run and produce correct output
- **Status:** pending

### Phase 5: Compliance Mapping
- [ ] Map controls to SEC 17a-4(f) requirements
- [ ] Map controls to FINRA Rule 4511
- [ ] Map controls to SOC 2 Trust Service Criteria
- [ ] Final deliverables checklist review
- **Status:** pending

## Documentation Artifacts (living — update INDEX.md when adding)

| Artifact | Path | Status |
|----------|------|--------|
| Master index | INDEX.md | Active |
| SRS | docs/srs/SRS-001.md | Draft |
| System design | docs/design/DESIGN-001.md | Draft |
| ADR-001 STRIDE | docs/adr/ADR-001-stride-over-owasp.md | Accepted |
| ADR-002 Trust hierarchy | docs/adr/ADR-002-trust-hierarchy.md | Accepted |
| ADR-003 Presidio | docs/adr/ADR-003-presidio-pii-scanner.md | Accepted |
| ADR-004 WORM log | docs/adr/ADR-004-worm-audit-log.md | Accepted |
| ADR-005 Tool layer perms | docs/adr/ADR-005-tool-layer-permissions.md | Accepted |

## Key Questions
1. Are Presidio dependencies available in target environment, or use regex-only PII scanner?
2. Should implementation code be runnable locally (pytest) or document-only stubs?
3. What jailbreak test patterns to use for system prompt hardening (FR-6)?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Target system: Jira/Confluence AI assistant on Bedrock | Bounded, realistic, tool-use-rich — ideal for STRIDE |
| Adapt STRIDE (not OWASP Top 10) to LLM surface | See ADR-001 |
| Trust hierarchy: system prompt > tool output > user > retrieved content | See ADR-002 |
| Presidio for PII detection | See ADR-003 |
| S3 Object Lock WORM for audit logs | See ADR-004 |
| Permissions enforced at tool layer, not model | See ADR-005 |
| Portfolio format: directory of artifacts + functional PoC | Career documentation goal; INDEX.md is rollup |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |

## Notes
- Every significant decision needs an ADR — add to docs/adr/ and update INDEX.md
- SRS acceptance criteria define PoC success criteria — implementation must satisfy FR-1 through FR-6
- Phase 1 (system definition) must be complete before identifying threats
- Final rollup = completed INDEX.md checklist
