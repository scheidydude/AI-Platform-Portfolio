# Software Requirements Specification

**Project:** AI Observability & Evals Framework  
**Version:** 0.1 (Draft)  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Draft

---

## 1. Purpose

This document defines the requirements for an evaluation (eval) framework designed to measure, monitor, and enforce quality standards for a production AI help desk system. The system under test (SUT) is a Jira/Confluence AI assistant that handles IT support and process requests.

This SRS covers:
- The SUT's behavioral requirements (what it must do correctly)
- The eval framework requirements (how correctness is measured)
- The CI integration requirements (how quality is enforced automatically)
- The production monitoring requirements (how quality is tracked over time)

---

## 2. Scope

### In Scope
- Simulated Jira/Confluence AI help desk system (SUT)
- LLM-as-judge evaluation pipeline
- Curated eval dataset (30+ cases)
- CI integration via GitHub Actions
- Production monitoring design (partial implementation)

### Out of Scope
- Live Jira/Confluence API integration (simulated)
- Real Datadog account (dashboard design only)
- User authentication/authorization
- Multi-tenant support

---

## 3. Stakeholders

| Role | Name | Interest |
|------|------|----------|
| Engineer / Author | David Scheiderman | Build & document |
| Hiring reviewer | TBD | Portfolio assessment |
| Simulated end user | IT support requester | Correct, helpful responses |

---

## 4. System Under Test — Functional Requirements

### 4.1 Input Processing

| ID | Requirement | Priority |
|----|-------------|----------|
| SUT-F-01 | System shall accept a natural language description of an IT or process problem | P0 |
| SUT-F-02 | System shall accept optional context (user department, timestamp) | P1 |
| SUT-F-03 | System shall classify input as one of: incident, service request, question, out-of-scope | P0 |
| SUT-F-04 | System shall extract the affected system name from the user message when present | P1 |

### 4.2 Knowledge Retrieval

| ID | Requirement | Priority |
|----|-------------|----------|
| SUT-F-05 | System shall search Confluence before creating any new Jira ticket | P0 |
| SUT-F-06 | System shall only reference Confluence articles that exist in the provided context | P0 |
| SUT-F-07 | System shall not hallucinate article titles, ticket numbers, or system names | P0 |

### 4.3 Response Generation

| ID | Requirement | Priority |
|----|-------------|----------|
| SUT-F-08 | System shall produce a structured response with a resolution or escalation path | P0 |
| SUT-F-09 | System shall escalate to a human agent when confidence is low | P0 |
| SUT-F-10 | System shall maintain professional, clear, and empathetic tone | P1 |
| SUT-F-11 | System shall not include PII from user input in generated ticket fields | P0 |
| SUT-F-12 | System shall not respond to out-of-scope requests; shall redirect to appropriate channel | P0 |

### 4.4 Multi-step Problems

| ID | Requirement | Priority |
|----|-------------|----------|
| SUT-F-13 | System shall decompose multi-step problems into discrete steps | P1 |
| SUT-F-14 | System shall request clarification when input is underspecified and clarification would materially improve resolution | P1 |

---

## 5. Eval Framework — Functional Requirements

### 5.1 Dataset

| ID | Requirement | Priority |
|----|-------------|----------|
| EVAL-F-01 | Eval dataset shall contain ≥30 labeled input/output/expected triples | P0 |
| EVAL-F-02 | Dataset shall cover all categories: straightforward, ambiguous, out-of-scope, PII, multi-step, adversarial | P0 |
| EVAL-F-03 | Each case shall include a human-written `notes` field explaining expected behavior | P1 |
| EVAL-F-04 | Dataset shall be stored as machine-parseable JSON | P0 |
| EVAL-F-05 | Dataset shall be version-controlled alongside judge prompt | P0 |

### 5.2 Judge Pipeline

| ID | Requirement | Priority |
|----|-------------|----------|
| EVAL-F-06 | Judge shall be a separate model call from the SUT — never the same model instance | P0 |
| EVAL-F-07 | Judge shall score: faithfulness (1–5), task_completion (1–5), tone (1–5), compliance (pass/fail), overall (1–5) | P0 |
| EVAL-F-08 | Judge shall output structured JSON only — no preamble | P0 |
| EVAL-F-09 | Judge output shall include a `reasoning` field (≤2 sentences) and a `flags` array | P1 |
| EVAL-F-10 | Judge prompt shall be versioned (semver) alongside eval dataset | P0 |
| EVAL-F-11 | Pipeline shall run end-to-end locally without external dependencies | P0 |

### 5.3 Scoring & Gates

| ID | Requirement | Priority |
|----|-------------|----------|
| EVAL-F-12 | P0 behaviors shall require 100% pass rate; failure blocks merge | P0 |
| EVAL-F-13 | P1 behaviors shall require ≥85% pass rate; failure is warning only | P1 |
| EVAL-F-14 | Overall average judge score shall remain ≥3.8/5; failure blocks merge | P0 |
| EVAL-F-15 | Gates shall be configurable via YAML without code changes | P1 |

### 5.4 Eval Run Artifacts

| ID | Requirement | Priority |
|----|-------------|----------|
| EVAL-F-16 | Each run shall produce a structured JSON artifact (run_id, commit, prompt version, results, summary) | P0 |
| EVAL-F-17 | Run artifact shall identify regressions by case ID versus baseline | P0 |

---

## 6. CI Integration — Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CI-F-01 | Eval workflow shall trigger on PR open and on changes to prompt files | P0 |
| CI-F-02 | Workflow shall run full eval suite against the changed prompt/model | P0 |
| CI-F-03 | Workflow shall compare results to baseline scores from main branch | P0 |
| CI-F-04 | Workflow shall block merge if P0 regressions detected | P0 |
| CI-F-05 | Workflow shall post a results summary as a PR comment | P1 |
| CI-F-06 | Workflow shall store eval run artifact as a CI artifact | P1 |

---

## 7. Production Monitoring — Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| MON-F-01 | System shall score a random 5% sample of production requests | P0 |
| MON-F-02 | System shall score 100% of requests that trigger fallback, escalation, or error | P0 |
| MON-F-03 | System shall score 100% of user-flagged dissatisfied requests | P0 |
| MON-F-04 | System shall score 100% of requests in first 24h after model/prompt change | P0 |
| MON-F-05 | System shall alert if 7-day rolling avg faithfulness or task_completion drops >0.3 points | P0 |
| MON-F-06 | System shall alert if any compliance failures occur within a 24h window | P0 |
| MON-F-07 | Dashboard shall expose: overall score (7d), P0 pass rate, compliance fail rate, score distribution, regressions per deploy | P1 |

---

## 8. Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-01 | Judge pipeline shall complete a 30-case eval run in <5 minutes | P1 |
| NFR-02 | All artifacts shall be stored in version control | P0 |
| NFR-03 | Judge prompt and dataset versions shall be co-pinned in run artifacts | P0 |
| NFR-04 | Code shall be written in Python 3.11+ | P1 |
| NFR-05 | No secrets shall be hardcoded; API keys via environment variables | P0 |

---

## 9. Constraints

- SUT is simulated — no live Jira/Confluence API calls required for PoC
- Datadog dashboard is a design artifact only (no live account assumed)
- All AI model calls use Anthropic Claude API
- Judge model must differ from SUT model (see ADR-0001)

---

## 10. Open Issues

| ID | Issue | Owner | Target |
|----|-------|-------|--------|
| OI-01 | ~~Confirm Python as implementation language~~ | Closed | Python 3.11+ — ADR-0004 |
| OI-02 | ~~Confirm GitHub Actions as CI platform~~ | Closed | GitHub Actions — ADR-0003 |
| OI-03 | ~~Determine if Datadog access available for live dashboard~~ | Closed | Design-only — ADR-0005 |
| OI-04 | Define SUT model version to pin for evals | David | Phase 2 |
