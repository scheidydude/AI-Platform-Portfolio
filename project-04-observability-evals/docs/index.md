# Project 4 — Documentation Index

**Project:** AI Observability & Evals  
**Purpose:** Career portfolio artifact. All design decisions, requirements, and architecture choices are captured here.  
**Status:** In progress  
**Last updated:** 2026-05-23 (Phase 5 complete — project done)

---

## How to Use This Index

Every artifact produced by this project is listed below. Use this as the final rollup for portfolio review. Each section links to the authoritative document; the "Status" column indicates readiness for review.

---

## Requirements

| Artifact | Description | Status | Link |
|----------|-------------|--------|------|
| SRS | Software Requirements Specification — full system requirements | Draft | [docs/srs.md](srs.md) |

---

## Architecture Decision Records (ADRs)

ADRs capture *why* a decision was made, not just what was decided. Each is immutable once accepted.

| # | Title | Status | Link |
|---|-------|--------|------|
| 0001 | Judge model separation from SUT | Accepted | [docs/adr/0001-judge-model-separation.md](adr/0001-judge-model-separation.md) |
| 0002 | Eval dataset format (JSON triples) | Accepted | [docs/adr/0002-eval-dataset-format.md](adr/0002-eval-dataset-format.md) |
| 0003 | CI platform selection (GitHub Actions) | Accepted | [docs/adr/0003-ci-platform.md](adr/0003-ci-platform.md) |
| 0004 | Implementation language (Python 3.11+) | Accepted | [docs/adr/0004-implementation-language.md](adr/0004-implementation-language.md) |
| 0005 | Production monitoring dashboard (design-only) | Accepted | [docs/adr/0005-datadog-design-only.md](adr/0005-datadog-design-only.md) |

---

## Design Documents

| Artifact | Description | Status | Link |
|----------|-------------|--------|------|
| System Design | End-to-end architecture of SUT + eval framework | Draft | [docs/design/system-design.md](design/system-design.md) |
| Eval Dataset Schema | Field definitions, enum values, and distribution targets for eval/dataset.json | Final | [docs/design/eval-dataset-schema.md](design/eval-dataset-schema.md) |
| Judge Pipeline Design | LLM-as-judge pipeline — prompt, scoring, output schema | Final | [docs/design/judge-pipeline-design.md](design/judge-pipeline-design.md) |
| CI Integration Design | GitHub Actions workflow, regression gates, PR reporting | Final | [docs/design/ci-integration-design.md](design/ci-integration-design.md) |
| Production Monitoring Design | Sampling strategy, drift detection, Datadog dashboard | Final | [docs/design/monitoring-design.md](design/monitoring-design.md) |

---

## Planning Artifacts

| Artifact | Description | Link |
|----------|-------------|------|
| Task Plan | Phase tracker, decisions, error log | [task_plan.md](../task_plan.md) |
| Findings | Research discoveries, open questions | [findings.md](../findings.md) |
| Progress Log | Session-by-session progress + test results | [progress.md](../progress.md) |

---

## Eval Artifacts

| Artifact | Description | Status | Link |
|----------|-------------|--------|------|
| Behavior Inventory | 19 behaviors (11 P0, 8 P1), fully traced to SRS | Final | [docs/design/behavior-inventory.md](design/behavior-inventory.md) |
| Eval Dataset | 30 cases across 6 scenario groups, all 19 behaviors covered | Final | [eval/dataset.json](../eval/dataset.json) |
| Judge Prompt v1 | Versioned judge prompt with rubric (4 dimensions + flags) | Final | [eval/prompts/judge_v1.md](../eval/prompts/judge_v1.md) |
| Eval Run Results | Structured artifacts from judge runs | Active | `eval/runs/` |

---

## Implementation Artifacts

| Artifact | Description | Status | Link |
|----------|-------------|--------|------|
| SUT | Simulated help desk AI (Haiku 4.5, structured JSON output) | Final | [src/sut.py](../src/sut.py) |
| Judge pipeline | LLM-as-judge scorer (Sonnet 4.6, per-case judgment) | Final | [src/judge_pipeline.py](../src/judge_pipeline.py) |
| Eval runner | Orchestrator — SUT → judge → run artifact → gate check | Final | [src/eval_runner.py](../src/eval_runner.py) |
| Report generator | Markdown PR comment generator with regression diff | Final | [src/generate_report.py](../src/generate_report.py) |
| Metrics emitter | DogStatsD metrics emitter (stdout + UDP modes) | Final | [src/metrics_emitter.py](../src/metrics_emitter.py) |
| Eval gates config | Regression thresholds (YAML, no code change required) | Final | [eval/gates.yaml](../eval/gates.yaml) |
| CI workflow | GitHub Actions — triggers, baseline cache, PR comment, gate enforcement | Final | [.github/workflows/eval.yml](../.github/workflows/eval.yml) |

---

## Final Rollup Checklist

Use at project end to verify portfolio completeness.

- [ ] SRS complete and reviewed
- [ ] All architectural decisions have ADRs
- [ ] All design docs written before implementation
- [x] Eval dataset: 30+ cases, all categories covered
- [x] Judge pipeline runs end-to-end locally
- [x] CI workflow triggers and blocks on P0 failures
- [x] Production monitoring design documented
- [x] This index is complete and all links resolve
