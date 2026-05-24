# Documentation Index — Project 03: Agentic Systems & MCP

**Purpose:** Running index of all project artifacts. Updated after every doc created or decision made.  
**Project:** 3-agent pipeline (planner → researcher → synthesizer) + MCP servers  
**Author:** David Scheiderman  
**Started:** 2026-05-23  
**Status:** In progress

---

## Requirements

| Doc | Status | Path | Description |
|-----|--------|------|-------------|
| SRS | `draft` | [docs/SRS.md](SRS.md) | Software Requirements Specification |

---

## Architecture Decision Records (ADRs)

| ADR | Status | Path | Decision |
|-----|--------|------|----------|
| ADR-000 | `accepted` | [docs/ADR/ADR-000-template.md](ADR/ADR-000-template.md) | ADR format template |
| ADR-001 | `accepted` | [docs/ADR/ADR-001-language-and-framework.md](ADR/ADR-001-language-and-framework.md) | Python (no framework abstraction) |
| ADR-002 | `accepted` | [docs/ADR/ADR-002-mcp-client-library.md](ADR/ADR-002-mcp-client-library.md) | `mcp` Python SDK (official, direct) |
| ADR-003 | `accepted` | [docs/ADR/ADR-003-web-search-provider.md](ADR/ADR-003-web-search-provider.md) | Self-hosted SearXNG at `https://search.scheidy.com/` |
| ADR-004 | `accepted` | [docs/ADR/ADR-004-state-persistence.md](ADR/ADR-004-state-persistence.md) | JSON to disk (atomic write via `os.replace()`) |
| ADR-005 | `accepted` | [docs/ADR/ADR-005-orchestration-pattern.md](ADR/ADR-005-orchestration-pattern.md) | Sequential; streaming eval deferred to Phase 4 |
| ADR-006 | `accepted` | [docs/ADR/ADR-006-llm-backend.md](ADR/ADR-006-llm-backend.md) | Self-hosted Qwen3-35B via llama.cpp at `http://ai.scheidy.com:8082` |

---

## Design Documents

| Doc | Status | Path | Description |
|-----|--------|------|-------------|
| System Design | `draft` | [docs/design/system-design.md](design/system-design.md) | End-to-end architecture, agent roles, data flow |
| Handoff Schemas | `not_started` | docs/design/handoff-schemas.md | Typed schemas for agent-to-agent communication |
| Tool Error Handling | `not_started` | docs/design/tool-error-handling.md | Error taxonomy and handling strategies |
| Loop Prevention | `complete` | [docs/design/loop-prevention.md](design/loop-prevention.md) | Loop detection and escape condition design |
| Orchestration | `complete` | [docs/design/orchestration.md](design/orchestration.md) | Sequential pipeline, resume, streaming eval |

---

## Planning Artifacts

| Doc | Status | Path | Description |
|-----|--------|------|-------------|
| Task Plan | `active` | [task_plan.md](../task_plan.md) | Phase tracking and progress |
| Findings | `active` | [findings.md](../findings.md) | Research discoveries |
| Progress Log | `active` | [progress.md](../progress.md) | Session-by-session log |

---

## Experiment & Lessons Learned

| Doc | Status | Path | Description |
|-----|--------|------|-------------|
| Failure Mode Experiments | `not_started` | docs/experiments.md | Results from deliberate failure injection |
| Lessons Learned | `not_started` | docs/lessons-learned.md | Production mitigations — Orchid V3 bridge doc |

---

## Rollup Summary

_Populated at project close (target: ~2026-06-02)_

- Decisions made: **6**
- ADRs accepted: **6** (ADR-001 through ADR-006)
- Experiments run: **0**
- Key lessons: _TBD_
