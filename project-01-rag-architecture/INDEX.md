# Project 01 — RAG Architecture: Artifact Index

**Author:** David Scheiderman
**Project:** RAG Architecture POC over SEC 10-K filings
**Start:** 2026-05-22
**Status:** In Progress (Phase 2 complete)

This index is the single source of truth for all artifacts. Update after every new document is created or status changes.

---

## Planning Artifacts

| Artifact | File | Status | Purpose |
|----------|------|--------|---------|
| Task Plan | `task_plan.md` | Active | Phase tracking, decisions log, error log |
| Findings | `findings.md` | Active | Research discoveries, open questions |
| Progress Log | `progress.md` | Active | Session log, test results, score history |

---

## Requirements & Specification

| Artifact | File | Status | Notes |
|----------|------|--------|-------|
| Software Requirements Spec (SRS) | `docs/SRS.md` | Draft | Functional/non-functional reqs, acceptance criteria |

---

## Architecture Decision Records (ADRs)

All 5 ADRs required by project spec. Eval impact section populated in Phases 3–4.

| ADR | File | Status | Decision |
|-----|------|--------|---------|
| ADR-001: Vector Store | `docs/adr/ADR-001-vector-store.md` | Draft | pgvector on Postgres (Docker) |
| ADR-002: Chunking Strategy | `docs/adr/ADR-002-chunking-strategy.md` | Decided | Hierarchical — section parents + sub-chunks |
| ADR-003: Hybrid Search | `docs/adr/ADR-003-hybrid-search.md` | Decided | Hybrid: dense + BM25 + RRF |
| ADR-004: Re-ranker | `docs/adr/ADR-004-reranker.md` | Decided | Include cross-encoder re-ranker |
| ADR-005: Embedding Model | `docs/adr/ADR-005-embedding-model.md` | Decided | nomic-embed-text local server (768 dims) |

---

## Design Documents

| Artifact | File | Status | Notes |
|----------|------|--------|-------|
| Chunking Strategy Decision | `docs/design/chunking-decision.md` | Complete | Hierarchical chosen — full rationale + data |
| Retrieval Architecture Design | `docs/design/retrieval-design.md` | Complete | Dense + BM25 + RRF + cross-encoder |
| Eval Methodology | `docs/design/eval-methodology.md` | Not started | Phase 3 deliverable |

---

## Evaluation Artifacts

| Artifact | File | Status | Notes |
|----------|------|--------|-------|
| Ground Truth Q&A Set | `eval/ground_truth.json` | Not started | Phase 3 — 20+ Q&A pairs |
| Eval Results (Phase 3 manual) | `eval/results/` | Not started | Phase 3 scores |
| Eval Results (Phase 4 automated) | `eval/results/` | Not started | LLM-as-judge scores per config |

---

## Source Code

| Module | Path | Status | Notes |
|--------|------|--------|-------|
| Ingestion pipeline | `src/ingestion/` | Complete | HTML → chunks → pgvector embeddings |
| Retrieval module | `src/retrieval/` | Complete | Dense + BM25 + RRF + cross-encoder; Flask API |
| Generation module | `src/generation/` | Not started | LLM call + citation grounding |
| Eval pipeline | `src/eval/` | Not started | LLM-as-judge automation |

---

## Final Deliverables (from spec)

| Deliverable | Status | Artifact |
|-------------|--------|---------|
| Working retrieval API | Complete | `src/retrieval/api.py` — Flask, `/search` + `/search/dense` |
| Chunking strategy writeup | Complete | `docs/design/chunking-decision.md` |
| Eval set 20+ Q&A pairs | Not started | `eval/ground_truth.json` |
| Automated eval pipeline | Not started | `src/eval/` |
| All 5 ADRs complete | Draft (5/5 stubbed) | `docs/adr/` |
| Before/after eval scores | Not started | `eval/results/` + ADR eval impact sections |

---

## Retrospective

| Artifact | File | Status |
|----------|------|--------|
| Project Retrospective | `docs/retrospective.md` | Not started (Phase 5) |

---

## How to Use This Index

1. After creating any new artifact, add a row to the appropriate section
2. Update Status column as work progresses: `Not started` → `Draft` → `Complete`
3. After Phase 4 eval runs, add score data to ADR eval impact sections and update status
4. Final rollup: every row should be `Complete` before project is done
