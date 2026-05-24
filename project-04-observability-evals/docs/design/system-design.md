# System Design — AI Observability & Evals Framework

**Version:** 0.1 (Draft)  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Draft

---

## 1. Overview

This document describes the end-to-end architecture of the eval framework for the Jira/Confluence AI help desk system.

There are two distinct systems:

1. **System Under Test (SUT)** — The AI help desk assistant (simulated for this PoC)
2. **Eval Framework** — The infrastructure for measuring, enforcing, and monitoring SUT quality

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    EVAL FRAMEWORK                       │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ Eval Dataset│───▶│  SUT Runner  │───▶│  Judge    │  │
│  │ (JSON)      │    │  (simulated) │    │  Pipeline │  │
│  └─────────────┘    └──────────────┘    └─────┬─────┘  │
│                                               │        │
│  ┌─────────────────────────────────────────── ▼ ─────┐ │
│  │              Run Artifact (JSON)                  │ │
│  │  run_id · commit · prompt_version · results       │ │
│  │  summary · regressions_from_baseline              │ │
│  └────────────────────────┬──────────────────────────┘ │
│                           │                            │
│            ┌──────────────┼──────────────┐             │
│            ▼              ▼              ▼             │
│      ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│      │  CI Gate │  │ PR Cmmt  │  │ Artifact Store│    │
│      │ (pass/   │  │ (summary)│  │ (GitHub)     │     │
│      │  block)  │  └──────────┘  └──────────────┘     │
│      └──────────┘                                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│               PRODUCTION MONITORING                     │
│                                                         │
│  Live traffic ──▶ Sampling filter ──▶ Async judge call  │
│                                            │            │
│                                     Metrics store       │
│                                            │            │
│                                    Datadog dashboard    │
│                                    + drift alerts       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Component Descriptions

### 3.1 System Under Test (SUT)

**Role:** The AI assistant being evaluated.

**For this PoC:** Simulated. The SUT is a Python function that accepts an input object and returns a structured response. It calls the Anthropic Claude API using a versioned prompt.

**Inputs:**
- `user_message` (string)
- `context` (optional dict: department, timestamp)
- Simulated Confluence search results (injected as context)

**Outputs:**
```json
{
  "ticket_type": "incident|request|question|out_of_scope",
  "affected_system": "string|null",
  "confluence_search_performed": true,
  "escalate": false,
  "response_to_user": "string",
  "ticket_fields": { "summary": "...", "description": "..." }
}
```

### 3.2 Eval Dataset

**Role:** Ground truth. 30+ curated input/output/expected triples.

**Format:** JSON array. See ADR-0002 for format decision.  
**Location:** `eval/dataset.json`  
**Versioning:** Committed to git; version tracked by git SHA.

### 3.3 Judge Pipeline

**Role:** Scores SUT outputs against expected behavior and rubric.

**Design:** See `docs/design/judge-pipeline-design.md` (forthcoming).

**Key constraint:** Judge is a separate model call from SUT. See ADR-0001.

**Judge model:** claude-sonnet-4-6 (default; may differ from SUT model)

**Output per case:**
```json
{
  "faithfulness": 4,
  "task_completion": 5,
  "tone": 4,
  "compliance": "pass",
  "overall": 4,
  "reasoning": "Response correctly searched Confluence first. Tone was professional.",
  "flags": []
}
```

### 3.4 Run Artifact

**Role:** Structured record of a complete eval run.

**Location:** `eval/runs/<run_id>.json`  
**Retained:** As CI artifact and in git (for baseline comparison)

### 3.5 CI Integration

**Platform:** GitHub Actions (pending confirmation, see ADR-0003)  
**Trigger:** PR open, changes to `eval/prompts/`, or changes to SUT model config  
**Behavior:** Run full suite → compare to baseline → gate on thresholds → comment on PR

### 3.6 Production Monitoring

**Design:** See `docs/design/monitoring-design.md` (forthcoming).  
**PoC scope:** Design document + partial implementation (async judge call + metrics emission)

---

## 4. Data Flow

```
1. PR opened with prompt change
2. GitHub Actions triggers eval workflow
3. Workflow loads dataset.json (30+ cases)
4. For each case:
   a. SUT runner generates response (Claude API call)
   b. Judge pipeline scores response (separate Claude API call)
   c. Score recorded in run artifact
5. Run artifact compared to baseline (main branch last run)
6. Gates evaluated:
   - P0 pass rate == 1.0?  → block if not
   - P1 pass rate >= 0.85? → warn if not
   - Overall avg >= 3.8?   → block if not
7. PR comment posted with summary
8. Run artifact uploaded as CI artifact
```

---

## 5. File Structure

```
project-04-observability-evals/
├── docs/
│   ├── index.md                    # Master artifact index
│   ├── srs.md                      # Software Requirements Specification
│   ├── adr/
│   │   ├── 0001-judge-model-separation.md
│   │   ├── 0002-eval-dataset-format.md
│   │   └── 0003-ci-platform.md
│   └── design/
│       ├── system-design.md        # This file
│       ├── behavior-inventory.md   # 10+ behaviors, P0/P1
│       ├── judge-pipeline-design.md
│       ├── ci-integration-design.md
│       └── monitoring-design.md
├── eval/
│   ├── dataset.json                # 30+ eval cases
│   ├── gates.yaml                  # Regression thresholds
│   ├── prompts/
│   │   └── judge_v1.md             # Versioned judge prompt
│   └── runs/                       # Eval run artifacts
├── src/
│   ├── sut.py                      # Simulated SUT
│   ├── judge_pipeline.py           # LLM-as-judge runner
│   └── eval_runner.py              # Orchestrates full eval suite
├── .github/
│   └── workflows/
│       └── eval.yml                # CI workflow
├── task_plan.md
├── findings.md
└── progress.md
```

---

## 6. Open Issues

| ID | Issue |
|----|-------|
| OI-01 | Confirm Python as implementation language |
| OI-02 | Confirm GitHub Actions as CI platform |
| OI-04 | Pin SUT model version |
