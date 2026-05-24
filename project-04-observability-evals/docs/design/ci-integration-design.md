# CI Integration Design — GitHub Actions Eval Workflow

**Version:** 1.0  
**Date:** 2026-05-23  
**Author:** David Scheiderman  
**Status:** Final (Phase 4)  
**Depends on:** [ADR-0003](../adr/0003-ci-platform.md), [ADR-0004](../adr/0004-implementation-language.md), [Judge Pipeline Design](judge-pipeline-design.md)

---

## 1. Purpose

This document defines the design of the GitHub Actions CI workflow for the eval suite. It covers: trigger conditions, job step ordering, baseline comparison strategy, PR comment format, artifact retention, and setup instructions for a new repository.

The authoritative implementation is `.github/workflows/eval.yml`.

---

## 2. Trigger Conditions

The workflow runs when files that affect eval quality change. Running on every commit would be wasteful; running never would miss regressions.

| Trigger | Paths | Rationale |
|---------|-------|-----------|
| `pull_request` (opened, reopened, synchronize) | `eval/prompts/**`, `eval/gates.yaml`, `eval/dataset.json`, `src/**` | Catch regressions before merge |
| `push` to `main` | Same paths | Update baseline after merge |
| `workflow_dispatch` | — (all files) | Manual trigger for debugging or forced baseline update |

**Why path filtering?** A PR that only touches `docs/` or `README.md` does not affect eval behavior and should not consume API quota.

---

## 3. Job Architecture

Single job `eval` on `ubuntu-latest`. Steps in order:

```
checkout
  └── setup python + pip cache
        └── install dependencies
              └── restore baseline from Actions cache
                    └── run eval suite (continue-on-error)
                          └── find run artifact path
                                └── generate report (markdown)
                                      └── post PR comment (PR only)
                                            └── upload run artifact
                                                  └── save + cache baseline (main push only)
                                                        └── enforce gate result (fail job if eval failed)
```

`continue-on-error: true` on the eval step lets downstream steps (report, PR comment, artifact upload) run even when the suite fails gates. The job fails at the final **Enforce gate result** step if the eval exit code was non-zero.

---

## 4. Baseline Comparison Strategy

The baseline is the last successful eval run from `main`. PRs compare against it to detect regressions.

**Mechanism: GitHub Actions cache**

- On `push` to `main` (gates passed): copy run artifact to `eval/baseline.json`, save to cache under key `eval-baseline-main-<sha>`.
- On `pull_request`: restore cache using `restore-keys: eval-baseline-main-` (prefix match returns most recent main baseline).
- `generate_report.py` receives `--baseline eval/baseline.json` only if the file exists. First-run behavior (no baseline): report shows current results only, no regression table.

**Why cache, not committed file?**
Committing a JSON file on every main push would pollute git history with large, non-human-readable blobs. The cache is ephemeral (7-day TTL), appropriate for a rolling baseline.

**Regression definition:** A case is a regression if it passed in the baseline run (`judgment.pass == true`) and fails in the current run (`judgment.pass == false`).

---

## 5. PR Comment Format

The comment is posted (or updated in-place) by `actions/github-script` on every PR run. Updating in-place prevents comment spam on repeated pushes to the same PR.

Structure:

```
## Eval Suite Results — run `<run_id>`

| Metric          | Value   | Gate     | Status |
|-----------------|---------|----------|--------|
| P0 pass rate    | 100.0%  | = 100%   | ✅ PASS |
| P1 pass rate    | 90.0%   | ≥ 85%    | ✅ PASS |
| Overall avg     | 4.2/5   | ≥ 3.8    | ✅ PASS |
| Compliance      | 0 fail  | 0 allowed| ✅ PASS |

**Gate result: ✅ PASS** — safe to merge

### Regressions vs baseline (`<baseline_run_id>`)

No regressions detected.

### Failed cases

| Case | Priority | Category | Flags |
|------|----------|----------|-------|
| eval_023 | P0 | compliance | PII_IN_TICKET |

<details>
<summary>All 30 results</summary>
...
</details>

> Commit `abc1234` · Dataset v1.0 · Judge prompt `judge_v1.md`
```

When no baseline exists (first run): the "Regressions" section is omitted. When gates fail, the gate result line reads `❌ FAIL — merge blocked`.

---

## 6. Artifact Retention

| Artifact | Storage | Retention |
|----------|---------|-----------|
| Per-run eval artifact | GitHub Actions artifact (`eval-run-<sha>`) | 90 days |
| Baseline | GitHub Actions cache (`eval-baseline-main-<sha>`) | 7 days (cache TTL) |

The per-run artifact is the authoritative record for auditing a specific run. The baseline is intentionally ephemeral — it is regenerated on every push to main.

---

## 7. Required Setup

To enable this workflow in a new repository:

1. **Add Anthropic API key secret:**
   - `Settings → Secrets and variables → Actions → New repository secret`
   - Name: `ANTHROPIC_API_KEY`
   - Value: your Anthropic API key

2. **Verify permissions:**
   - `Settings → Actions → General → Workflow permissions`
   - Enable: "Read and write permissions" (required for PR comments)

3. **No branch protection required** to trigger the workflow, but to enforce the gate block on merge, add a branch protection rule for `main` requiring the `eval / Eval Suite` status check to pass.

---

## 8. Cost Model

Approximate per-run cost for 30 cases on current model versions:

| Component | Model | Calls | Est. tokens | Est. cost |
|-----------|-------|-------|-------------|-----------|
| SUT | claude-haiku-4-5 | 30 | ~500 in / ~300 out each | ~$0.03 |
| Judge | claude-sonnet-4-6 | 30 | ~1500 in / ~200 out each | ~$0.15 |
| Prompt cache savings | — | — | ~80% cache hit on system prompts | ~−$0.04 |
| **Total per run** | | | | **~$0.14** |

At 20 PRs/day: ~$2.80/day. Well within Anthropic free tier or small paid budget.

---

## 9. Local Replication

Any step in the CI workflow can be run locally:

```bash
# Full run
ANTHROPIC_API_KEY=sk-... python src/eval_runner.py

# First 5 cases only
ANTHROPIC_API_KEY=sk-... python src/eval_runner.py --limit 5

# Without API calls (gate/report smoke test)
python src/eval_runner.py --dry-run

# Generate report from existing run artifact
python src/generate_report.py --run eval/runs/<run_id>.json --output report.md
```

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-05-23 | Initial design — Phase 4 |
