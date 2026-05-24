# Task Plan — Project 4: AI Observability & Evals

## Goal
Build a production-grade eval framework for a Jira/Confluence AI help desk system. Prove the system works via LLM-as-judge pipeline wired into CI.

## Current Phase
**Phase 5** — Production monitoring design

## Phases

| # | Phase | Status | Days |
|---|-------|--------|------|
| 1 | Use case definition + behavior inventory | `complete` | 1–2 |
| 2 | Eval dataset (30+ input/output/expected triples) | `complete` | 3–5 |
| 3 | LLM-as-judge pipeline | `complete` | 6–8 |
| 4 | CI integration (GitHub Actions) | `complete` | 9–10 |
| 5 | Production monitoring design | `complete` | 11–12 |

## Deliverables Checklist

- [x] Behavior inventory (10+ behaviors, P0/P1 tagged)
- [x] Eval dataset: 30+ curated input/output/expected triples (JSON)
- [x] Judge prompt with structured scoring rubric
- [x] Automated judge pipeline (runs locally)
- [x] CI workflow (GitHub Actions) — triggers on prompt/model change
- [x] Regression detection with configurable gates
- [x] Production monitoring design document
- [x] Datadog dashboard design

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
| docs/design/eval-dataset-schema.md | Eval case schema — field definitions and enum values | 2 |
| eval/dataset.json | 30-case eval dataset, all 19 behaviors covered | 2 |
| docs/design/judge-pipeline-design.md | Judge pipeline architecture, rubric, gate config | 3 |
| eval/prompts/judge_v1.md | Versioned judge system prompt | 3 |
| eval/gates.yaml | Gate thresholds (YAML, no code change required) | 3 |
| src/sut.py | Simulated SUT (Haiku 4.5, structured JSON output) | 3 |
| src/judge_pipeline.py | LLM-as-judge scorer (Sonnet 4.6) | 3 |
| src/eval_runner.py | Orchestrator — full eval loop, gate check, run artifact | 3 |
| requirements.txt | Python dependencies | 3 |
| docs/design/ci-integration-design.md | CI workflow design, baseline strategy, cost model, setup guide | 4 |
| src/generate_report.py | Markdown PR comment generator with regression diff | 4 |
| .github/workflows/eval.yml | GitHub Actions workflow — triggers, baseline cache, PR comment, gate enforcement | 4 |
| docs/design/monitoring-design.md | Sampling strategy, 4 alerts, 8 dashboard panels, drift detection, DogStatsD integration | 5 |
| src/metrics_emitter.py | DogStatsD metrics emitter — stdout (dev) + UDP (prod) modes | 5 |
