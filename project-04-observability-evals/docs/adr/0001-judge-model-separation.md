# ADR-0001 — Judge Model Separation from System Under Test

**Date:** 2026-05-23  
**Status:** Accepted  
**Author:** David Scheiderman

---

## Context

The eval framework uses an LLM to score the outputs of another LLM (the system under test, SUT). A design choice must be made: can the judge be the same model instance as the SUT, or must it be a separate model call?

This is a foundational decision that affects eval reliability and trust. If the same model judges its own outputs, several failure modes appear:
- The model may have learned to produce outputs that it also rates highly, regardless of actual quality
- Systematic biases in the model's reasoning appear in both the output and the judgment, making them invisible to the judge
- Self-evaluation creates a circular dependency: a regressed model would also regress its own scoring, masking the regression

---

## Decision

**The judge shall always be a separate model call from the SUT.**

Specifically:
- The judge is invoked as a fresh, independent API call with a distinct system prompt
- The judge model version may differ from the SUT model version
- The judge and SUT shall never share state, context window, or conversation history

---

## Consequences

**Positive:**
- Eval scores remain trustworthy even when the SUT model changes
- Regressions in the SUT do not automatically degrade judge scoring
- Judge prompt can be improved independently of SUT prompt
- Enables A/B comparison of different SUT models using a fixed judge

**Negative:**
- Two API calls per eval case (doubled cost)
- Judge itself can have biases — mitigated by using a different model family or version than SUT when possible
- Requires maintaining two versioned prompts (SUT + judge)

**Neutral:**
- Judge model choice is a separate decision (see future ADR); defaulting to claude-sonnet-4-6

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| Self-evaluation (SUT judges own output) | Circular; masks regressions; not credible for external review |
| Human-only evaluation | Does not scale to 30+ cases per CI run |
| Rule-based scoring only | Cannot assess faithfulness, tone, or nuanced task completion |
