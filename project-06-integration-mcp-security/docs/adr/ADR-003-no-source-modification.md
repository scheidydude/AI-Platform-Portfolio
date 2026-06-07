# ADR-003 — Zero Modification Constraint on P03 and P05 Source Files

**Status:** Accepted  
**Date:** 2026-06-06  
**Deciders:** David Scheiderman

---

## Context

P06 integrates two independently complete projects (P03 and P05). Both were developed and tested in isolation. This ADR records the explicit decision not to modify their source files and the reasoning behind it.

---

## Decision

No file within `../project-03-agentic-mcp/src/` or `../project-05-security-compliance/src/` shall be modified as part of P06 work.

---

## Rationale

### 1. The integration premise requires it

The portfolio claim for P06 is: "independently verified components work when composed." That claim is falsified if P06 modifies either component to make the composition work. Modifying the components to fit the integration is adaptation, not integration.

A reviewer comparing P03 before and after would see changes that exist only because of P06 — a sign the components were not actually designed with composable interfaces.

### 2. It forces honest documentation of interface gaps

If two components cannot be composed without modification, that is an architectural finding worth documenting. ADR-002 explicitly records that P03's `ResearcherAgent.run()` has no overridable hook for tool result content, and that this gap would require a proxy pattern in a production implementation. This is portfolio-grade analysis.

Modifying researcher.py to add a hook would hide this finding.

### 3. P03 and P05 must remain independently runnable

Both projects have passing test suites. Any modification to their source files risks breaking those tests or introducing regressions visible in their own CI. The constraint ensures the independence guarantee in NFR-1 and NFR-2 is structurally enforced, not just stated.

---

## Scope Clarification

**What "source files" means:**
- Any `.py` file under `../project-03-agentic-mcp/src/`
- Any `.py` file under `../project-05-security-compliance/src/`

**What is not covered (permitted):**
- Adding new files to P03 or P05 (e.g., a `pyproject.toml` if P05 lacked one — though this was rejected for other reasons in ADR-001)
- Modifying `tests/`, `docs/`, or `findings.md` in parent projects (P05's `findings.md` is explicitly updated in Phase 4 per the spec)
- Reading P03 and P05 source files (obviously permitted)

---

## Consequences

- P06 owns all integration code. Integration surface is explicit and auditable in `src/secure_researcher.py`.
- Architectural gaps (like the missing hook in Point 1) must be documented rather than patched.
- If a future P03 refactor adds the hook, P06 can adopt it with a change only to `secure_researcher.py`.
- The constraint is verifiable: `git diff ../project-03-agentic-mcp/src/ ../project-05-security-compliance/src/` must show no changes at project completion.
