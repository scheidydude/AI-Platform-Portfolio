# Findings — Project 4: AI Observability & Evals

## System Under Test (SUT)

**Name:** Jira/Confluence AI Help Desk Tool

**Input:** User natural language description of IT or process problem

**Actions:**
1. Search Confluence for relevant articles
2. Optionally create or update a Jira ticket

**Output:** Structured response — resolution or escalation path

---

## Behavior Inventory (from spec)

| Behavior | Category | Priority |
|----------|----------|---------|
| Correctly identifies ticket type (bug vs. request vs. question) | Classification | P0 |
| Searches Confluence before creating a new ticket | Process adherence | P0 |
| Does not hallucinate Confluence article titles | Faithfulness | P0 |
| Escalates to human when confidence is low | Safety | P0 |
| Tone is professional and non-condescending | Style | P1 |
| Does not include PII in ticket descriptions | Compliance | P0 |
| Correctly extracts affected system from user message | Extraction | P1 |

> Need to expand to 10+ behaviors. Additional behaviors to define in Phase 1.

---

## Eval Dataset Structure (from spec)

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
  "notes": "..."
}
```

### Dataset composition targets

| Category | Count |
|----------|-------|
| Straightforward, in-scope | 10 |
| Ambiguous/underspecified | 6 |
| Out-of-scope | 4 |
| Compliance edge cases (PII) | 4 |
| Multi-step problems | 4 |
| High-confidence wrong answers | 2 |
| **Total** | **30** |

---

## Judge Prompt Structure (from spec)

- Separate model from SUT
- Structured JSON output only
- Dimensions: faithfulness (1-5), task_completion (1-5), tone (1-5), compliance (pass/fail), overall (1-5), reasoning, flags[]
- Prompt must be versioned alongside eval dataset

---

## CI Gates (from spec)

```yaml
eval_gates:
  p0_behaviors:
    min_pass_rate: 1.0
    block_on_failure: true
  p1_behaviors:
    min_pass_rate: 0.85
    block_on_failure: false
  overall_average:
    min_score: 3.8
    block_on_failure: true
```

---

## Production Sampling Strategy (from spec)

| Trigger | Sample Rate |
|---------|-------------|
| Random | 5% |
| Fallback/escalation/error | 100% |
| User flagged dissatisfied | 100% |
| First 24h after model/prompt change | 100% |

---

## Open Questions

- [ ] Does user have actual Jira/Confluence access, or is this fully simulated?
- [ ] Preferred CI platform (GitHub Actions assumed)?
- [ ] Datadog access available for dashboard, or design-only?
- [ ] Python preferred for pipeline implementation?
