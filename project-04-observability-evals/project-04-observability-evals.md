# Project 4 — AI Observability & Evals
**Skill area:** AI observability and evaluations  
**Format:** Simulated enterprise (design + document)  
**Estimated duration:** 12 days

---

## Overview

Design and build an eval framework for a production AI system. Use a real use case — the Jira/Confluence help ticket tool is ideal. Build an LLM-as-judge pipeline that scores outputs on accuracy, groundedness, and tone, then wire it into CI so every model or prompt change gets automatically evaluated.

This is your biggest gap area and the most in-demand skill in AI Architect hiring right now. Start here even if it feels less exciting than the build projects.

---

## The mental model

Evals are the difference between *"I shipped an AI feature"* and *"I can prove this AI feature works."* In regulated industries, the latter is not optional.

There are three layers:

- **Unit evals** — test a specific behavior in isolation (does the model correctly identify a Jira ticket number from this input?)
- **Integration evals** — test the full pipeline end-to-end (does the right ticket get updated with the right content?)
- **Production monitoring** — continuous scoring of live traffic with drift detection

This project covers all three. Most teams only do the first and wonder why production misbehaves.

---

## Phase 1 — Use case definition (Days 1–2)

### Target system

Use the Jira/Confluence help ticket tool as your simulated system. Define what it does precisely enough to write tests for it.

**System definition:**
- Input: a user's natural language description of an IT or process problem
- Actions: search Confluence for relevant articles, optionally create or update a Jira ticket
- Output: a structured response to the user with a resolution or escalation path

### Behavior inventory

List every discrete behavior the system should exhibit. These become your test cases.

| Behavior | Category | Priority |
|---|---|---|
| Correctly identifies ticket type (bug vs. request vs. question) | Classification | P0 |
| Searches Confluence before creating a new ticket | Process adherence | P0 |
| Does not hallucinate Confluence article titles | Faithfulness | P0 |
| Escalates to human when confidence is low | Safety | P0 |
| Tone is professional and non-condescending | Style | P1 |
| Does not include PII in ticket descriptions | Compliance | P0 |
| Correctly extracts affected system from user message | Extraction | P1 |

---

## Phase 2 — Eval dataset (Days 3–5)

Build a curated dataset of at least 30 input/output/expected triples. Quality over quantity — poorly labeled eval data is worse than less data.

### Dataset structure

```json
{
  "id": "eval_001",
  "category": "classification",
  "priority": "P0",
  "input": {
    "user_message": "Hey, I can't log into the Workday portal since this morning. Getting a 403 error.",
    "context": { "user_department": "Finance", "system_time": "09:15" }
  },
  "expected": {
    "ticket_type": "incident",
    "affected_system": "Workday",
    "escalate": false,
    "confluence_search_performed": true
  },
  "notes": "Should classify as incident not request. Should not escalate. Must search Confluence first."
}
```

### Dataset composition targets

| Category | Count | Why |
|---|---|---|
| Straightforward, in-scope requests | 10 | Happy path baseline |
| Ambiguous or underspecified inputs | 6 | Tests clarification behavior |
| Out-of-scope requests | 4 | Tests refusal and handoff |
| Compliance edge cases (PII in input) | 4 | Tests redaction behavior |
| Multi-step problems | 4 | Tests decomposition |
| High-confidence wrong answers | 2 | Tests calibration |

---

## Phase 3 — LLM-as-judge pipeline (Days 6–8)

### Judge design principles

- The judge is a separate model call from the system under test — never use the same model instance for both
- The judge prompt must be versioned alongside the eval dataset
- Judge outputs must be structured (JSON) for automated scoring
- Include a reasoning field — it is the most valuable debugging output

### Judge prompt template

```
You are an expert evaluator for an enterprise AI help desk system.

Your job is to assess whether the system's response meets quality criteria.
You must be strict, consistent, and base your evaluation only on the information provided.

## Input
User message: {user_message}
System context: {context}

## System response
{system_response}

## Expected behavior
{expected_behavior}

## Evaluation criteria
Score each dimension from 1–5 where 5 = fully meets criteria, 1 = fails completely.

Return ONLY valid JSON, no preamble or explanation outside the JSON object:
{
  "faithfulness": <1-5>,
  "task_completion": <1-5>,
  "tone": <1-5>,
  "compliance": <"pass"|"fail">,
  "overall": <1-5>,
  "reasoning": "<two sentences max>",
  "flags": ["<issue1>", "<issue2>"]
}
```

### Scoring rubric definitions

**Faithfulness (1–5):** Does the response contain only claims supported by retrieved context or verified facts? Penalize any hallucinated article titles, ticket numbers, or system names.

**Task completion (1–5):** Does the response accomplish what the user needed? A technically accurate response that does not resolve the user's problem scores 2 or lower.

**Tone (1–5):** Is the response professional, clear, and appropriately empathetic? Penalize condescension, excessive jargon, and robotic phrasing.

**Compliance (pass/fail):** Does the response avoid including, echoing, or storing PII from the user's input in generated ticket fields?

---

## Phase 4 — CI integration (Days 9–10)

Every model or prompt change should automatically run the eval suite. This makes evals a forcing function for quality, not an afterthought.

### Pipeline design

```
PR opened / prompt file changed
  → Trigger eval workflow (GitHub Actions or Jenkins)
  → Run full eval suite against new prompt/model
  → Score all 30+ cases via LLM judge
  → Compare to baseline scores from main branch
  → Generate diff report
  → Block merge if P0 regressions exist
  → Post results summary to PR as comment
```

### Regression detection

Define pass/fail thresholds per priority level:

```yaml
eval_gates:
  p0_behaviors:
    min_pass_rate: 1.0       # P0 behaviors must pass 100%
    block_on_failure: true
  p1_behaviors:
    min_pass_rate: 0.85      # P1 behaviors must pass 85%
    block_on_failure: false  # Warn only
  overall_average:
    min_score: 3.8           # Overall judge score must stay above 3.8/5
    block_on_failure: true
```

### Eval result artifact

Store every eval run as a structured artifact:

```json
{
  "run_id": "eval_run_20260522_143200",
  "commit": "abc1234",
  "prompt_version": "v1.4.2",
  "model": "claude-sonnet-4-20250514",
  "results": [...],
  "summary": {
    "total": 30,
    "passed": 27,
    "failed": 3,
    "p0_pass_rate": 1.0,
    "p1_pass_rate": 0.83,
    "average_score": 4.1
  },
  "regressions_from_baseline": ["eval_014", "eval_022"]
}
```

---

## Phase 5 — Production monitoring design (Days 11–12)

Design (and partially implement) continuous eval for live traffic.

### Sampling strategy

You cannot judge every production request — it is too expensive. Design a sampling strategy:

- **Random sample:** 5% of all requests scored by judge
- **Triggered sample:** 100% of requests that triggered a fallback, escalation, or error
- **User-flagged:** 100% of requests where user indicated dissatisfaction
- **Canary:** 100% of requests during the first 24 hours after a model or prompt change

### Drift detection

Track eval scores over time and alert on drift:

```
llm_eval.faithfulness.avg        alert if 7-day rolling avg drops > 0.3 points
llm_eval.task_completion.avg     alert if drops > 0.3 points
llm_eval.compliance.fail_rate    alert if any failures in 24h window
```

### Datadog dashboard design

Document the dashboard you would build (or build it if you have Datadog access):

| Panel | Metric | Chart type |
|---|---|---|
| Overall quality score | `llm_eval.overall.avg` (7d rolling) | Line |
| P0 pass rate | `llm_eval.p0_pass_rate` | Stat card |
| Compliance failures | `llm_eval.compliance.fail_rate` | Stat card with alert color |
| Score distribution | `llm_eval.overall` histogram | Bar |
| Regressions per deploy | `llm_eval.regressions` by version | Bar |

---

## Deliverables checklist

- [ ] Behavior inventory for the target system (10+ behaviors)
- [ ] Eval dataset: 30+ curated input/output/expected triples
- [ ] Judge prompt with structured scoring rubric
- [ ] Automated judge pipeline (can run locally)
- [ ] CI workflow that runs evals on prompt/model change
- [ ] Regression detection with configurable gates
- [ ] Production monitoring design document
- [ ] Datadog dashboard design (or working dashboard)

---

## Where to start right now

Write the behavior inventory first — before any code. List every behavior the system should exhibit and mark each P0 or P1. Then write 5 eval cases by hand, run them through a judge prompt manually (paste into Claude), and see if the scoring is consistent and useful. If the judge scores are not telling you anything actionable, fix the rubric before building the automation.
