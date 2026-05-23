# Project 01 — RAG Architecture: Artifact Index

**Author:** David Scheiderman
**Project:** RAG Architecture POC over SEC 10-K filings
**Start:** 2026-05-22
**Status:** Complete — all 5 phases done

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
| Software Requirements Spec (SRS) | `docs/SRS.md` | Complete | Functional/non-functional reqs — all acceptance criteria met |

---

## Architecture Decision Records (ADRs)

All 5 ADRs required by project spec. Eval impact section populated in Phases 3–4.

| ADR | File | Status | Decision |
|-----|------|--------|---------|
| ADR-001: Vector Store | `docs/adr/ADR-001-vector-store.md` | Decided | pgvector on Postgres (Docker) |
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
| Eval Methodology | `docs/design/eval-methodology.md` | Complete | 20-question set, recall@K method, Phase 3 scores |

---

## Evaluation Artifacts

| Artifact | File | Status | Notes |
|----------|------|--------|-------|
| Ground Truth Q&A Set | `eval/ground_truth.json` | Complete | 20 Q&A pairs (10 single, 5 multi, 5 OOS) with GT chunk IDs |
| Eval Results (Phase 3 manual) | `eval/results/phase3_retrieval_scores.json` | Complete | R@1=0.933, R@3=1.0, R@5=1.0; OOS 5/5 |
| Eval Results (Phase 4 automated) | `eval/results/phase4_lm_judge_scores.json` | Complete | 3 configs × 15 questions; hybrid mean=4.600, dense mean=4.445 |

---

## Source Code

| Module | Path | Status | Notes |
|--------|------|--------|-------|
| Ingestion pipeline | `src/ingestion/` | Complete | HTML → chunks → pgvector embeddings |
| Retrieval module | `src/retrieval/` | Complete | Dense + BM25 + RRF + cross-encoder; Flask API |
| Generation module | `src/generation/` | Complete | Qwen3.6-35B via OpenAI-compatible API; citation grounding |
| Eval pipeline | `src/eval/` | Complete | LLM-as-judge; run_eval.py; 3-config ablation |

---

## Final Deliverables (from spec)

| Deliverable | Status | Artifact |
|-------------|--------|---------|
| Working retrieval API | ✅ Complete | `src/retrieval/api.py` — Flask, `/search` + `/search/dense` |
| Chunking strategy writeup | ✅ Complete | `docs/design/chunking-decision.md` |
| Eval set 20+ Q&A pairs | ✅ Complete | `eval/ground_truth.json` — 20 questions |
| Automated eval pipeline | ✅ Complete | `src/eval/run_eval.py` — 3 configs × 15 questions |
| All 5 ADRs complete | ✅ Complete | `docs/adr/` — all 5 Decided with eval impact data |
| Before/after eval scores | ✅ Complete | Hybrid R@1=0.933 vs dense R@1=0.533; ADR-003 + ADR-004 |

---

## Retrospective

| Artifact | File | Status |
|----------|------|--------|
| Project Retrospective | `docs/retrospective.md` | Complete | What went well, harder than expected, learnings, final scores |

---

## How to Use This Index

1. After creating any new artifact, add a row to the appropriate section
2. Update Status column as work progresses: `Not started` → `Draft` → `Complete`
3. After Phase 4 eval runs, add score data to ADR eval impact sections and update status
4. Final rollup: every row should be `Complete` before project is done
