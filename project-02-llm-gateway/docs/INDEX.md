# LLM Gateway — Document Index

**Project:** Project 02 — LLM Gateway / Cost Governance  
**Owner:** David Scheiderman  
**Started:** 2026-05-23  
**Status:** In Progress

Career documentation artifact. All decisions, designs, and tradeoffs recorded here for portfolio rollup.

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

---

## Design Documents

| ID | Title | Status | Date |
|----|-------|--------|------|
| [DESIGN-001](design/DESIGN-001-architecture.md) | System Architecture Overview | Draft → validate against Phase 1 build | 2026-05-23 |

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

- [ ] All ADRs reflect final decisions (none superseded without successor)
- [ ] SRS marked Final with acceptance criteria verified
- [ ] DESIGN-001 updated to match what was actually built
- [ ] Phase 5 comparison doc added to Design section
- [ ] All deliverables from `task_plan.md` checked off
- [ ] One-paragraph executive summary added to top of this INDEX
