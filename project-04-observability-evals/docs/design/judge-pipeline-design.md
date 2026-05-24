# Judge Pipeline Design — LLM-as-Judge Evaluation

**Version:** 1.0  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Final (Phase 3)  
**Depends on:** [ADR-0001](../adr/0001-judge-model-separation.md), [ADR-0002](../adr/0002-eval-dataset-format.md), [ADR-0004](../adr/0004-implementation-language.md)

---

## 1. Purpose

This document defines the design of the LLM-as-judge evaluation pipeline: how SUT outputs are scored, what scoring dimensions mean, how judgments aggregate into a run artifact, and how gate thresholds are applied. This is the authoritative reference for implementing `src/judge_pipeline.py` and `src/eval_runner.py`.

---

## 2. Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       eval_runner.py                        │
│                                                             │
│  dataset.json ──▶  for each case:                           │
│                       │                                     │
│              ┌────────▼────────┐                            │
│              │   sut.py        │  Claude Haiku 4.5 (SUT)    │
│              │   run_sut(case) │  separate API call         │
│              └────────┬────────┘                            │
│                       │ sut_output                          │
│              ┌────────▼────────┐                            │
│              │ judge_pipeline  │  Claude Sonnet 4.6 (judge) │
│              │ judge_case(...) │  separate API call         │
│              └────────┬────────┘                            │
│                       │ judgment                            │
│              ┌────────▼────────┐                            │
│              │ result record   │                            │
│              └────────┬────────┘                            │
│                       │                                     │
│              aggregate results                              │
│              compute summary                                │
│              check gates (gates.yaml)                       │
│                       │                                     │
│              ┌────────▼────────┐                            │
│              │ run artifact    │  eval/runs/<run_id>.json   │
│              └─────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

**Key constraint (ADR-0001):** The SUT and judge are always separate API calls. They never share context. The judge model (Sonnet 4.6) differs from the SUT model (Haiku 4.5) to reduce same-model bias.

---

## 3. Component Responsibilities

### 3.1 `src/sut.py` — Simulated System Under Test

**Role:** Simulates the production help desk AI. In this PoC, it is a Claude API call with a versioned help desk system prompt.

**Model:** `claude-haiku-4-5-20251001` — intentionally different from judge model.

**Prompt caching:** The SUT system prompt is cached (`cache_control: ephemeral`) since it is the same across all 30 cases in a run.

**Input:** An eval case dict (contains `input.user_message` and `input.context`).

**Output:** Structured JSON:

```json
{
  "ticket_type": "incident|service_request|question|out_of_scope|null",
  "confluence_searched": true,
  "escalate": false,
  "ask_clarification": false,
  "clarification_question": null,
  "ticket_fields": {
    "summary": "...",
    "description": "...",
    "priority": "Critical|High|Medium|Low",
    "system": "..."
  },
  "response_to_user": "..."
}
```

### 3.2 `src/judge_pipeline.py` — LLM-as-Judge

**Role:** Scores a single SUT output against the eval case's `expected` specification.

**Model:** `claude-sonnet-4-6` — more capable than SUT; separate call per ADR-0001.

**Prompt caching:** The judge system prompt (`eval/prompts/judge_v1.md`) is cached since it is the same across all cases in a run.

**Input:** The full eval case (input + expected) and the SUT output dict.

**Output:** Judgment dict (see Section 4).

### 3.3 `src/eval_runner.py` — Orchestrator

**Role:** Drives the full eval loop, aggregates results, checks gates, and writes the run artifact.

**Entry point:** `python src/eval_runner.py [--limit N] [--dry-run]`

**Exit codes:** 0 = gates pass, 1 = gates fail (consumed by CI).

---

## 4. Scoring Rubric

Per SRS requirement EVAL-F-07, the judge scores four dimensions per case.

### 4.1 `faithfulness` (integer 1–5)

Measures whether the SUT invented facts not present in the provided context.

| Score | Meaning |
|-------|---------|
| 5 | No hallucinations. Only references articles/tickets/systems from `input.context`. |
| 4 | Minor imprecision but nothing clearly invented. |
| 3 | One reference that appears hallucinated but is ambiguous. |
| 2 | One clear hallucination (invented article title, ticket number, or system name). |
| 1 | Multiple hallucinations or egregious fabrication. |

**N/A handling:** Cases where no context is provided (empty `context`) score faithfulness=5 by default — there is nothing to fabricate from.

### 4.2 `task_completion` (integer 1–5)

Measures whether the SUT took the correct action(s) relative to `expected`.

| Score | Meaning |
|-------|---------|
| 5 | Correct ticket type; all required actions taken; all required fields present. |
| 4 | Correct ticket type; minor omission (e.g., missing one field). |
| 3 | Partially correct — major action taken but important element missing or wrong. |
| 2 | Wrong ticket type OR critical required action missing. |
| 1 | Completely wrong — wrong classification AND wrong action. |

### 4.3 `tone` (integer 1–5)

Measures professional quality and appropriate empathy of `response_to_user`.

| Score | Meaning |
|-------|---------|
| 5 | Clear, professional, context-appropriate empathy. Not robotic, not condescending. |
| 4 | Mostly professional; minor issue (slightly stiff or slightly casual). |
| 3 | Noticeably robotic or condescending, but not harmful. |
| 2 | Clearly unprofessional, dismissive, or performatively hollow empathy. |
| 1 | Rude, offensive, or completely inappropriate. |

### 4.4 `compliance` (string: `"pass"` or `"fail"`)

Binary. Measures PII handling only — whether PII from the user message leaked into ticket fields or the response text.

**`"fail"` if any of:**
- User's name, email address, employee ID, or SSN appears in `ticket_fields.summary`
- User's name, email address, employee ID, or SSN appears in `ticket_fields.description`
- User's name or email address is echoed back in `response_to_user` (BEH-015)

**`"pass"` if:** None of the above violations occur.

**Note:** Faithfulness violations (hallucinated articles, ticket numbers) are scored under `faithfulness`, not `compliance`.

### 4.5 `overall` (integer 1–5)

Holistic quality score. Not a simple average — the `judge_focus` field from `expected` determines weighting.

| `judge_focus` | Dimension emphasized |
|---------------|---------------------|
| `ticket_classification` | task_completion × 2 |
| `faithfulness` | faithfulness × 2 |
| `pii_compliance` | compliance gates overall ≤ 2 if "fail" |
| `clarification` | task_completion × 2 (did it ask correctly?) |
| `escalation` | task_completion × 2 (did it escalate?) |
| `extraction` | task_completion × 2 (correct fields extracted?) |
| `tone` | tone × 2 |
| `scope` | task_completion × 2 (out-of-scope identified?) |
| `multi_system` | task_completion × 2 (both systems handled?) |

When `compliance == "fail"`, `overall` is capped at 2 regardless of other scores.

---

## 5. Per-Case Pass/Fail Determination

A case **passes** if all of the following hold:
1. `compliance == "pass"`
2. `overall >= 3`
3. For P0 cases: `task_completion >= 3`

A case **fails** if any condition is not met.

This is implemented in `eval_runner.case_passes()` and is the authoritative definition. The gate thresholds in `eval/gates.yaml` operate on aggregate pass rates, not individual cases.

---

## 6. Run Artifact Schema

Written to `eval/runs/<run_id>.json` after each full run.

```json
{
  "run_id": "a1b2c3d4",
  "timestamp": "2026-05-23T18:00:00Z",
  "dataset_version": "1.0",
  "total_cases": 30,
  "summary": {
    "p0_pass_rate": 1.0,
    "p1_pass_rate": 0.9,
    "overall_avg": 4.1,
    "compliance_failures": []
  },
  "gate_result": {
    "pass": true,
    "failures": []
  },
  "results": [
    {
      "case_id": "eval_001",
      "priority": "P0",
      "category": "classification",
      "sut_output": { "...": "..." },
      "judgment": {
        "case_id": "eval_001",
        "scores": {
          "faithfulness": 5,
          "task_completion": 5,
          "tone": 4,
          "compliance": "pass",
          "overall": 5
        },
        "reasoning": "Correct incident classification. Confluence search performed. PII absent from ticket.",
        "flags": [],
        "pass": true
      }
    }
  ]
}
```

`run_id` is an 8-character hex string derived from `uuid.uuid4()`. Stable across re-reads.

---

## 7. Gate Configuration (`eval/gates.yaml`)

Gates are checked after all cases run. Configurable without code changes per SRS EVAL-F-15.

```yaml
p0_pass_rate: 1.0          # 100% — any P0 failure blocks merge
p1_pass_rate: 0.85         # 85% minimum — failure is warning only (CI exit 0)
overall_avg_min: 3.8       # Holistic quality floor — failure blocks merge
compliance_failures_allowed: 0  # Any PII leak blocks merge
```

Gate behavior in CI:
- `p0_pass_rate` failure → `exit 1` (blocks merge)
- `overall_avg_min` failure → `exit 1` (blocks merge)
- `compliance_failures_allowed` exceeded → `exit 1` (blocks merge)
- `p1_pass_rate` failure → warning in PR comment, `exit 0` (does not block)

---

## 8. Judge Prompt Versioning

The judge prompt lives at `eval/prompts/judge_v1.md`. Version number is part of the filename.

Rules:
- **Patch fix** (fix wording, add example): bump in-file `version` field only, keep `judge_v1.md`
- **Scoring dimension change** (add/remove/rename a dimension): new file `judge_v2.md`, update pipeline to reference it
- **Both dataset and prompt change in same PR**: record both versions in the run artifact

The judge prompt version is not currently recorded in the run artifact (Phase 3 scope). Adding it is tracked as a future improvement.

---

## 9. Prompt Caching Strategy

Both the SUT and judge use Anthropic prompt caching (`cache_control: ephemeral`) on their respective system prompts. Within a single eval run of 30 cases:

- **SUT system prompt:** Cached after first case. Cases 2–30 hit cache. Estimated 95%+ cache hit rate.
- **Judge system prompt:** Cached after first case. Cases 2–30 hit cache. Same hit rate.

Cache TTL is 5 minutes. A 30-case run completes in under 5 minutes at typical API throughput, so the cache stays warm throughout.

---

## 10. Error Handling

| Failure mode | Handling |
|-------------|---------|
| SUT API call fails | Retry once; if still fails, record `{"parse_error": true}`, score as 1/1/1/fail/1, mark case failed |
| SUT output is not valid JSON | Regex-extract JSON block; if none found, same fallback as above |
| Judge API call fails | Same retry/fallback pattern; case marked failed |
| Judge output is not valid JSON | Fallback judgment with all-1 scores and `PARSE_ERROR` flag |
| `gates.yaml` missing | Use hardcoded defaults (p0=1.0, p1=0.85, avg=3.8) |

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-05-23 | Initial design — Phase 3 |
