# ADR-0003 — CI Platform Selection

**Date:** 2026-05-23  
**Status:** Accepted  
**Author:** David Scheiderman

---

## Context

The eval framework needs a CI platform to automatically run the eval suite when a prompt file or model version changes. The platform must:
- Trigger on pull request open and on changes to specific file paths
- Run Python scripts in a reproducible environment
- Store structured artifacts (eval run JSON)
- Post a summary comment to the PR
- Block merge on configurable failure conditions

This is a portfolio project. The CI workflow itself is a deliverable and will be read by hiring reviewers.

---

## Decision

**Use GitHub Actions as the CI platform.**

This is a draft decision pending confirmation. Assumed because:
- The project lives in a GitHub repository
- GitHub Actions is the default and most visible choice for portfolio projects
- No existing Jenkins/CircleCI/other CI infrastructure was specified

---

## Consequences

**Positive:**
- Zero setup cost — GitHub Actions is included in GitHub repos
- Workflow YAML lives in `.github/workflows/` and is visible in the repo
- Native PR comment API via `gh` CLI or `actions/github-script`
- Artifact storage via `actions/upload-artifact`
- Familiar to most engineering hiring reviewers

**Negative:**
- API key (Anthropic) must be stored as a GitHub Secret — adds setup step
- Free tier has usage limits; 30-case eval run should stay well within them
- Less flexibility than self-hosted runners for complex environments

**Neutral:**
- Workflow is portable; could be adapted to Jenkins or CircleCI with minimal changes

---

## Alternatives Considered

| Alternative | Reason Rejected (or deferred) |
|-------------|-------------------------------|
| Jenkins | No existing infrastructure assumed; higher setup cost for portfolio |
| CircleCI | Requires external account; no advantage over GitHub Actions for this use case |
| Local-only (no CI) | Does not satisfy the "CI integration" deliverable |

---

## Resolution

OI-02 closed 2026-05-23. GitHub Actions confirmed by project author.
