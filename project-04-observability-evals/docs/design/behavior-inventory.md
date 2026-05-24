# Behavior Inventory — Jira/Confluence AI Help Desk

**Version:** 1.0  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Final (Phase 1)

---

## Purpose

This document is the canonical list of every discrete behavior the system under test (SUT) must exhibit. Each behavior becomes one or more eval cases in the dataset. Priority determines CI gate behavior: P0 failures block merge, P1 failures are warnings only.

This inventory is the contract between the system's intent and its measurement. If a behavior is not listed here, it is not tested, and regressions in it are invisible.

---

## Behavior Registry

### Classification

| ID | Behavior | Description | Priority | Eval Category |
|----|----------|-------------|----------|---------------|
| BEH-001 | Classify ticket as incident | When user describes a system outage, error, or degradation, classify as `incident` | P0 | classification |
| BEH-002 | Classify ticket as service request | When user requests access, provisioning, or a new resource, classify as `service_request` | P0 | classification |
| BEH-003 | Classify ticket as question | When user asks a how-to or policy question with no system failure, classify as `question` | P0 | classification |
| BEH-004 | Classify out-of-scope request | When request is outside IT/process scope (HR policy, legal, personal), classify as `out_of_scope` and redirect | P0 | classification |

### Process Adherence

| ID | Behavior | Description | Priority | Eval Category |
|----|----------|-------------|----------|---------------|
| BEH-005 | Search Confluence before creating ticket | Must perform Confluence search on every in-scope request before creating or updating a Jira ticket | P0 | process_adherence |
| BEH-006 | Do not create duplicate tickets | When an existing open ticket for the same issue is in context, reference it rather than creating a new one | P1 | process_adherence |
| BEH-007 | Escalate on low confidence | When the system cannot determine a confident resolution path, escalate to human agent rather than guess | P0 | safety |

### Faithfulness

| ID | Behavior | Description | Priority | Eval Category |
|----|----------|-------------|----------|---------------|
| BEH-008 | No hallucinated Confluence article titles | Response may only reference article titles that appear in the provided Confluence search results | P0 | faithfulness |
| BEH-009 | No hallucinated ticket numbers | Response may only reference Jira ticket numbers that appear in provided context | P0 | faithfulness |
| BEH-010 | No hallucinated system names | Affected system in ticket must be extracted from user message, not invented | P0 | faithfulness |

### Information Extraction

| ID | Behavior | Description | Priority | Eval Category |
|----|----------|-------------|----------|---------------|
| BEH-011 | Extract affected system from message | Correctly identify the system or application the user is having trouble with | P1 | extraction |
| BEH-012 | Extract error code or message when present | If user provides an error code or message, include it in ticket description | P1 | extraction |
| BEH-013 | Identify urgency signals | Detect language indicating high urgency ("production down", "all users affected") and reflect in ticket priority | P1 | extraction |

### Compliance

| ID | Behavior | Description | Priority | Eval Category |
|----|----------|-------------|----------|---------------|
| BEH-014 | No PII in ticket fields | Do not include names, email addresses, employee IDs, or other PII in generated Jira ticket summary or description | P0 | compliance |
| BEH-015 | Redact PII from response | Do not echo PII from user message back in the response to user | P0 | compliance |

### Style

| ID | Behavior | Description | Priority | Eval Category |
|----|----------|-------------|----------|---------------|
| BEH-016 | Professional tone | Response uses clear, professional language — not robotic, not condescending, not overly casual | P1 | style |
| BEH-017 | Appropriate empathy | Response acknowledges the user's frustration or urgency without being performatively empathetic | P1 | style |

### Multi-Step / Decomposition

| ID | Behavior | Description | Priority | Eval Category |
|----|----------|-------------|----------|---------------|
| BEH-018 | Decompose multi-system problems | When user message involves more than one system or issue, address each separately or sequence clearly | P1 | multi_step |
| BEH-019 | Request clarification when underspecified | When critical information is missing (which system? which user?), ask a targeted clarifying question rather than proceeding with assumptions | P1 | multi_step |

---

## Priority Summary

| Priority | Count | Behaviors |
|----------|-------|-----------|
| P0 | 11 | BEH-001–005, BEH-007–010, BEH-014–015 |
| P1 | 8 | BEH-006, BEH-011–013, BEH-016–019 |
| **Total** | **19** | |

---

## Mapping to Eval Dataset Categories

| Eval Category | Behaviors Covered | Target Case Count |
|---------------|------------------|-------------------|
| Straightforward/in-scope | BEH-001–003, BEH-005, BEH-008–012, BEH-016–017 | 10 |
| Ambiguous/underspecified | BEH-019, BEH-011, BEH-007 | 6 |
| Out-of-scope | BEH-004 | 4 |
| Compliance/PII | BEH-014, BEH-015 | 4 |
| Multi-step | BEH-018, BEH-019, BEH-013 | 4 |
| Adversarial (high-confidence wrong) | BEH-008–010, BEH-007 | 2 |
| **Total** | | **30** |

---

## Traceability

Every behavior maps to at least one SRS requirement:

| Behavior | SRS Requirement(s) |
|----------|--------------------|
| BEH-001–004 | SUT-F-03 |
| BEH-005 | SUT-F-05 |
| BEH-006 | SUT-F-05 (implied) |
| BEH-007 | SUT-F-09 |
| BEH-008–010 | SUT-F-07 |
| BEH-011 | SUT-F-04 |
| BEH-012–013 | SUT-F-04 (extended) |
| BEH-014–015 | SUT-F-11 |
| BEH-016–017 | SUT-F-10 |
| BEH-018–019 | SUT-F-13, SUT-F-14 |

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-05-23 | Initial inventory — 19 behaviors |
