# Eval Dataset Schema — Jira/Confluence AI Help Desk

**Version:** 1.0  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Final (Phase 2)  
**Format authority:** [ADR-0002](../adr/0002-eval-dataset-format.md)

---

## Purpose

This document defines the canonical field schema for `eval/dataset.json`. It is the contract between dataset authors and the judge pipeline. Any field not defined here is not a valid field.

---

## Top-Level Dataset Object

```json
{
  "version": "string — semver, bumped when schema changes",
  "created": "string — ISO 8601 date",
  "description": "string — one-line dataset summary",
  "cases": [ ...case objects... ]
}
```

---

## Case Object

```json
{
  "id": "eval_NNN",
  "category": "string — see enum below",
  "priority": "P0 | P1",
  "behaviors": ["BEH-NNN", "..."],
  "input": { ...input object... },
  "expected": { ...expected object... },
  "notes": "string — required; explains what to look for and why"
}
```

### `id`

Format: `eval_NNN` (zero-padded three digits). Unique and stable — never renumber existing cases.

### `category`

One of: `classification`, `process_adherence`, `faithfulness`, `safety`, `compliance`, `extraction`, `style`, `multi_step`, `adversarial`.

Maps to behavior categories in `docs/design/behavior-inventory.md`.

### `priority`

- `P0` — failure blocks CI merge gate
- `P1` — failure is a warning; does not block

### `behaviors`

Array of `BEH-NNN` IDs from the behavior inventory. At least one required. Drives traceability from case → behavior → SRS requirement.

---

## Input Object

```json
{
  "user_message": "string — required",
  "context": {
    "confluence_results": [ ...article objects... ],
    "open_tickets": [ ...ticket objects... ]
  }
}
```

### `input.user_message`

The verbatim message from the user to the help desk AI. Required.

### `input.context`

Optional. Omit for cases where no external context is relevant.

**`confluence_results`** — array of article objects:
```json
{
  "title": "string",
  "url": "string",
  "excerpt": "string — first ~200 chars of article body"
}
```

**`open_tickets`** — array of ticket objects:
```json
{
  "id": "string — e.g. HELP-1234",
  "summary": "string",
  "status": "string — e.g. Open, In Progress",
  "created": "string — ISO 8601 date"
}
```

---

## Expected Object

The `expected` object defines what correct SUT behavior looks like. Not all fields are required per case — include only the fields the judge should evaluate for this case.

```json
{
  "ticket_type": "incident | service_request | question | out_of_scope | null",
  "ticket_created": true | false,
  "confluence_search_required": true | false,
  "escalate": true | false,
  "ask_clarification": true | false,
  "ticket_fields": { ...ticket field constraints... },
  "response_must": ["string", "..."],
  "response_must_not": ["string", "..."],
  "judge_focus": "string"
}
```

### `expected.ticket_type`

The expected classification of the user request:

| Value | When |
|-------|------|
| `incident` | System outage, degradation, or error affecting users |
| `service_request` | Request for access, provisioning, or new resource |
| `question` | How-to or policy question; no system failure |
| `out_of_scope` | Outside IT/process scope; should redirect |
| `null` | No ticket should be created (e.g., pure clarification exchange) |

### `expected.ticket_created`

Boolean. Whether the SUT should have produced a `create_ticket` action.

### `expected.confluence_search_required`

Boolean. Whether the SUT must have performed a Confluence search before any ticket action. Derived from BEH-005.

### `expected.escalate`

Boolean. Whether the SUT should escalate to a human agent rather than resolve autonomously. Derived from BEH-007.

### `expected.ask_clarification`

Boolean. Whether the SUT should ask a targeted clarifying question. Derived from BEH-019.

### `expected.ticket_fields`

Constraints on generated ticket fields. Include only the fields relevant to the case.

```json
{
  "priority": "Critical | High | Medium | Low",
  "system": "string — expected extracted system name",
  "summary_must_not_contain": ["string", "..."],
  "description_must_include": ["string", "..."],
  "description_must_not_contain": ["string", "..."]
}
```

### `expected.response_must`

Array of plain-language constraints the SUT response must satisfy. Used by judge as evaluation criteria.

Examples:
- `"Acknowledge user frustration without being performative"`
- `"Reference only articles present in input.context.confluence_results"`
- `"Ask which system is affected"`

### `expected.response_must_not`

Array of plain-language constraints the SUT response must NOT violate.

Examples:
- `"Echo the user's name or email address back"`
- `"Invent a Confluence article title not in provided context"`
- `"Include a Jira ticket number not present in open_tickets"`

### `expected.judge_focus`

A single string naming the primary evaluation dimension for this case. Helps the judge weight its scoring. One of:

- `"ticket_classification"` — did the SUT pick the right ticket type?
- `"faithfulness"` — did the SUT fabricate facts?
- `"pii_compliance"` — did the SUT handle PII correctly?
- `"clarification"` — did the SUT ask the right question?
- `"escalation"` — did the SUT escalate when it should have?
- `"extraction"` — did the SUT extract the right fields?
- `"tone"` — did the SUT maintain appropriate style and empathy?
- `"scope"` — did the SUT correctly identify out-of-scope requests?
- `"multi_system"` — did the SUT handle multiple systems/issues correctly?

---

## Distribution Targets

Per the behavior inventory mapping table:

| Scenario Group | Cases | Key Behaviors |
|----------------|-------|---------------|
| Straightforward / in-scope | 10 | BEH-001–003, BEH-005, BEH-008–012, BEH-016–017 |
| Ambiguous / underspecified | 6 | BEH-019, BEH-011, BEH-007 |
| Out-of-scope | 4 | BEH-004 |
| Compliance / PII | 4 | BEH-014, BEH-015 |
| Multi-step | 4 | BEH-018, BEH-019, BEH-013 |
| Adversarial | 2 | BEH-008–010, BEH-007 |
| **Total** | **30** | |

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-05-23 | Initial schema definition |
