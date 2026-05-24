# ADR-001: Use STRIDE Instead of OWASP Top 10 for LLM Threat Modeling

**Date:** 2026-05-23  
**Status:** Accepted  
**Deciders:** David Scheiderman  
**Project:** Project 05 — Enterprise Security & Compliance

---

## Context

We need a threat modeling framework for an enterprise LLM-powered AI assistant with tool use. Two dominant options exist: OWASP Top 10 (or OWASP LLM Top 10) and STRIDE.

The system under analysis has characteristics that distinguish it from traditional web applications:
- Input is natural language — the attack surface cannot be enumerated
- The model is stateful during a session — earlier context affects later behavior
- Tool use extends blast radius — a compromised agent can take real-world actions
- The boundary between data and instructions is inherently blurry

OWASP Top 10 was designed for web application vulnerabilities (injection, broken auth, XSS, etc.) and maps poorly to LLM threat surfaces. OWASP LLM Top 10 exists but is a list of symptoms (e.g., "Prompt Injection") rather than a structured threat analysis methodology.

STRIDE is a threat analysis methodology (not a vulnerability list) developed by Microsoft for structured threat discovery. It organizes threats by what the attacker achieves, making it framework-agnostic and adaptable to novel surfaces.

---

## Decision

Use STRIDE as the primary threat modeling methodology for this system, adapted to the LLM attack surface.

STRIDE categories map to LLM threats as follows:

| Category | LLM Application |
|----------|----------------|
| **S**poofing | Identity claims in natural language; system prompt impersonation |
| **T**ampering | Prompt injection via retrieved documents; context poisoning |
| **R**epudiation | Deniable model actions (no audit trail for tool use) |
| **I**nformation disclosure | System prompt extraction; PII exfiltration; cross-user leakage |
| **D**enial of service | Token exhaustion; recursive tool loops; prompt bombs |
| **E**levation of privilege | Injected instructions claiming new permissions; role confusion |

---

## Consequences

**Positive:**
- Structured methodology produces systematic coverage — no category skipped
- Each STRIDE category maps cleanly to concrete LLM attack patterns
- STRIDE is recognized in compliance contexts (SOC 2 risk assessment)
- Framework is methodology, not checklist — adaptable as LLM threat surface evolves

**Negative:**
- STRIDE does not natively address LLM-specific concerns (hallucination, training data poisoning, model inversion) — these require additional coverage
- Less prescriptive than OWASP LLM Top 10; requires more analyst judgment
- STRIDE is less well-known in ML/AI communities than OWASP

**Mitigations:**
- Supplement STRIDE with OWASP LLM Top 10 as a cross-reference checklist (not the primary framework)
- Document LLM-specific additions explicitly in findings.md

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| OWASP Top 10 (web) | Designed for web apps; maps poorly to LLM surface |
| OWASP LLM Top 10 | Symptom list, not methodology; no systematic coverage guarantee |
| PASTA | Heavier process; more suited to large organization risk programs |
| TRIKE | Less industry recognition; harder to map to compliance frameworks |

---

*Related: [DESIGN-001](../design/DESIGN-001.md), [findings.md](../../findings.md)*
