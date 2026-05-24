# ADR-0002 — Eval Dataset Format (JSON Triples)

**Date:** 2026-05-23  
**Status:** Accepted  
**Author:** David Scheiderman

---

## Context

The eval dataset needs a storage format. It will be:
- Read by the judge pipeline (automated)
- Reviewed by humans when authoring or auditing cases
- Version-controlled in git
- Diffed when cases are added, modified, or removed
- Extended to 30+ cases over the course of the project

The format must balance machine parseability, human readability, and git-friendliness.

---

## Decision

**Store the eval dataset as a JSON array of case objects (one file: `eval/dataset.json`).**

Each case object (a "triple") has the shape:

```json
{
  "id": "eval_001",
  "category": "classification",
  "priority": "P0",
  "input": {
    "user_message": "...",
    "context": { "user_department": "...", "system_time": "..." }
  },
  "expected": {
    "ticket_type": "incident",
    "affected_system": "Workday",
    "escalate": false,
    "confluence_search_performed": true
  },
  "notes": "Human-readable explanation of expected behavior and edge case."
}
```

Fields are mandatory unless noted:
- `id` — unique, sequential, stable across edits
- `category` — one of: classification, process_adherence, faithfulness, safety, style, compliance, extraction, multi_step, adversarial
- `priority` — P0 or P1
- `input.user_message` — required
- `input.context` — optional (omit for cases where context is not relevant)
- `expected` — object with behavior-specific fields; not all fields required per case
- `notes` — required; explains what to look for and why this case exists

---

## Consequences

**Positive:**
- Single file is easy to load in Python with `json.load()`
- Human-readable and auditable
- Git diffs are line-level and meaningful
- Schema is extensible (add fields without breaking old cases)
- `id` field enables stable regression tracking across runs

**Negative:**
- Large arrays in a single JSON file can produce noisy diffs when IDs shift; mitigated by always appending, never reordering
- No schema enforcement at write time; mitigated by adding JSON Schema validation to the pipeline

**Neutral:**
- 30–50 cases at ~500 bytes each ≈ 15–25 KB; file size is not a concern

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| CSV | Cannot represent nested input/expected objects cleanly |
| YAML | More human-friendly but less consistent parsing; ambiguous types |
| One JSON file per case | Too many files; harder to load and diff holistically |
| SQLite | Overkill for 30 cases; poor git diffability |
