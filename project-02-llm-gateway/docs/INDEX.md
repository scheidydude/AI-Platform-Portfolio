# LLM Gateway — Document Index

**Project:** Project 02 — LLM Gateway / Cost Governance  
**Owner:** David Scheiderman  
**Started:** 2026-05-23  
**Status:** Complete

Career documentation artifact. All decisions, designs, and tradeoffs recorded here for portfolio rollup.

---

## Executive Summary

Built a production-shaped LLM gateway in Python (FastAPI / SQLite / Prometheus) over 10 days, covering four routing strategies (static, cost-aware, fallback, shadow), three quota enforcement modes (hard block, soft cap, downgrade), per-team token accounting with tiktoken, structured NDJSON logging, a Prometheus metrics endpoint, and an embedded HTML cost dashboard. Backends are pluggable via an OpenAI-compatible adapter; Ollama serves as the free local backend alongside any OpenAI-compatible cloud provider. The project closes with a grounded vendor comparison (this build vs. LiteLLM vs. Bifrost) written from firsthand implementation experience — covering the non-obvious hard parts: streaming token accounting, SQLite quota races, shadow task GC, and the architectural coupling between downgrade enforcement and routing. Primary takeaway: LiteLLM solves the same problem plus five years of edge cases; the narrow cases where building wins are shadow routing, deeply custom quota logic, and non-standard auth integration.

---

## Requirements

| ID | Title | Status |
|----|-------|--------|
| [SRS-001](srs/SRS-001-llm-gateway.md) | Software Requirements Specification | Draft |

---

## Architecture Decision Records

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-001](adr/ADR-001-fastapi.md) | Framework: FastAPI | Accepted | 2026-05-23 |
| [ADR-002](adr/ADR-002-state-store.md) | State Store: SQLite → Redis | Accepted | 2026-05-23 |
| [ADR-003](adr/ADR-003-token-counting.md) | Token Counting: tiktoken + reconcile | Accepted | 2026-05-23 |
| [ADR-004](adr/ADR-004-team-config.md) | Team Config: YAML | Accepted | 2026-05-23 |
| [ADR-005](adr/ADR-005-rate-limiting.md) | Rate Limiting: In-Memory Sliding Window | Accepted | 2026-05-23 |
| [ADR-006](adr/ADR-006-metrics.md) | Metrics Backend: Prometheus | Accepted | 2026-05-23 |
| [ADR-007](adr/ADR-007-dashboard.md) | Cost Dashboard: Embedded HTML + Vanilla JS | Accepted | 2026-05-23 |
| [ADR-008](adr/ADR-008-routing-strategies.md) | Multi-Backend Routing: 4 Strategies + Ollama | Accepted | 2026-05-23 |

---

## Design Documents

| ID | Title | Status | Date |
|----|-------|--------|------|
| [DESIGN-001](design/DESIGN-001-architecture.md) | System Architecture Overview | Final | 2026-05-23 |
| [DESIGN-002](design/DESIGN-002-vendor-comparison.md) | Build vs. Buy: LLM Gateway Vendor Comparison | Final | 2026-05-23 |

---

## Planning Artifacts

| File | Purpose |
|------|---------|
| [task_plan.md](../task_plan.md) | Phase tracking, deliverables, error log |
| [findings.md](../findings.md) | Research discoveries, stack decisions, risks |
| [progress.md](../progress.md) | Session log, test results |

---

## Final Rollup Checklist

_Complete when project closes (Day 10)._

- [x] All ADRs reflect final decisions (none superseded without successor)
- [x] SRS marked Final with acceptance criteria verified
- [x] DESIGN-001 updated to match what was actually built
- [x] Phase 5 comparison doc added to Design section
- [x] All deliverables from `task_plan.md` checked off
- [x] One-paragraph executive summary added to top of this INDEX
