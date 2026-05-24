# ADR-0004 — Implementation Language (Python)

**Date:** 2026-05-23  
**Status:** Accepted  
**Author:** David Scheiderman

---

## Context

The eval pipeline, SUT simulator, and CI runner need an implementation language. Requirements:
- First-class Anthropic SDK support
- Strong JSON handling
- Compatible with GitHub Actions runners
- Readable by hiring reviewers in AI/ML roles

## Decision

**Python 3.11+.**

## Consequences

**Positive:**
- `anthropic` Python SDK is the reference implementation — best docs, most examples
- `json`, `pathlib`, `subprocess` in stdlib cover all pipeline needs
- GitHub Actions `ubuntu-latest` runners include Python 3.11+
- Dominant language in AI/ML hiring; maximizes reviewer familiarity

**Negative:**
- Slower startup than Go/Node for CLI tools; acceptable for a 30-case eval suite

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| TypeScript/Node | Anthropic SDK is fine but Python SDK has more eval tooling in ecosystem |
| Go | Less common in AI/ML roles; no significant advantage here |
| Shell scripts | Cannot cleanly handle JSON scoring or Anthropic API calls |
