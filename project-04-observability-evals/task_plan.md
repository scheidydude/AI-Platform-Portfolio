# Task Plan — Project 4: AI Observability & Evals

## Goal
Build a production-grade eval framework for a Jira/Confluence AI help desk system. Prove the system works via LLM-as-judge pipeline wired into CI.

## Current Phase
**Phase 1** — Use case definition

## Phases

| # | Phase | Status | Days |
|---|-------|--------|------|
| 1 | Use case definition + behavior inventory | `complete` | 1–2 |
| 2 | Eval dataset (30+ input/output/expected triples) | `not_started` | 3–5 |
| 3 | LLM-as-judge pipeline | `not_started` | 6–8 |
| 4 | CI integration (GitHub Actions) | `not_started` | 9–10 |
| 5 | Production monitoring design | `not_started` | 11–12 |

## Deliverables Checklist

- [ ] Behavior inventory (10+ behaviors, P0/P1 tagged)
- [ ] Eval dataset: 30+ curated input/output/expected triples (JSON)
- [ ] Judge prompt with structured scoring rubric
- [ ] Automated judge pipeline (runs locally)
- [ ] CI workflow (GitHub Actions) — triggers on prompt/model change
- [ ] Regression detection with configurable gates
- [ ] Production monitoring design document
- [ ] Datadog dashboard design

## Documentation-First Rule

Every phase must produce formal docs BEFORE implementation:
- Design decisions → ADR in `docs/adr/`
- Architecture → Design doc in `docs/design/`
- Requirements → `docs/srs.md` (already created)
- All artifacts indexed in `docs/index.md`

Update `docs/index.md` after every new artifact. Final rollup = complete index with all links resolving.

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Target system | Jira/Confluence help desk | Defined in project spec |
| Judge model | claude-sonnet-4-6 (separate from SUT) | Avoid same-model bias |
| Eval format | JSON triples (id, input, expected, notes) | Machine-parseable, diff-friendly |
| CI platform | GitHub Actions | Default assumption; adjust if needed |
| Scoring | 1–5 per dimension + compliance pass/fail | Per project spec rubric |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |

## Files Created/Modified

| File | Purpose | Phase |
|------|---------|-------|
| task_plan.md | This file | Setup |
| findings.md | Research & discoveries | Setup |
| progress.md | Session log | Setup |
