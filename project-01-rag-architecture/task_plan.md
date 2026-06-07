# Task Plan — RAG Architecture POC

**Project:** Project 01 — RAG Architecture (Career Path)
**Start:** 2026-05-22
**Target Complete:** 2026-06-02 (11 days)
**Goal:** Functional RAG POC over SEC 10-K filings + full career documentation artifact set

---

## Phases

| # | Phase | Days | Status | Owner |
|---|-------|------|--------|-------|
| 0 | Scaffolding & Setup | 0 | complete | - |
| 1 | Corpus & Ingestion | 1–2 | complete | - |
| 2 | Retrieval (hybrid + re-rank) | 3–5 | complete | - |
| 3 | Eval Set (manual ground truth) | 6–7 | complete | - |
| 4 | LLM-as-Judge Automation | 8–10 | complete | - |
| 5 | ADR Writeup + Final Docs | 11 | complete | - |

---

## Phase 0 — Scaffolding (complete)

### Deliverables
- [x] Directory structure
- [x] INDEX.md (running artifact index)
- [x] task_plan.md (this file)
- [x] findings.md
- [x] progress.md
- [x] SRS.md stub
- [x] ADR stubs (5 required ADRs)

---

## Phase 1 — Corpus & Ingestion (Days 1–2)

### Objective
Ingest 10–15 SEC 10-K PDFs. Implement and compare 3 chunking strategies. Write chunking decision document.

### Tasks
- [x] Download 10–15 10-K PDFs from EDGAR
- [x] Set up Docker Compose: Postgres + pgvector
- [x] Implement fixed-size chunking (512 tokens, 64 overlap)
- [x] Implement semantic chunking (SemanticChunker / semantic-chunkers)
- [x] Implement hierarchical chunking (parent section + sub-chunks)
- [x] Manually inspect 20–30 chunks per strategy
- [x] Write chunking strategy decision doc → `docs/design/chunking-decision.md`
- [x] Fill ADR-002 (chunking strategy)

### Key Decisions Pending
- Embedding model: `text-embedding-3-small` (API) vs. local llama.cpp
- Chunking strategy winner

### Deliverable
`docs/design/chunking-decision.md` — written rationale for chosen strategy

---

## Phase 2 — Retrieval (Days 3–5)

### Objective
Hybrid search (dense + BM25 + RRF fusion) + cross-encoder re-ranker + citation grounding.

### Tasks
- [x] Implement dense retrieval via pgvector
- [x] Implement BM25 sparse retrieval (rank_bm25)
- [x] Implement RRF fusion
- [x] Integrate cross-encoder re-ranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- [x] Build citation grounding (chunk IDs through full pipeline)
- [x] Write retrieval architecture design doc → `docs/design/retrieval-design.md`
- [x] Fill ADR-003 (hybrid search), ADR-004 (re-ranker) — status Decided

### Key Decisions Pending
- K value for retrieval
- Re-ranker threshold

---

## Phase 3 — Eval Set (Days 6–7)

### Objective
20+ Q&A pairs with manual ground truth chunk references. Score manually.

### Tasks
- [x] Write 10 single-source questions
- [x] Write 5 multi-source questions
- [x] Write 5 out-of-scope questions
- [x] Manually identify correct source chunk(s) per question
- [x] Manually score: retrieval recall@K, faithfulness, answer relevance
- [x] Save to `eval/ground_truth.json`
- [x] Write eval methodology doc → `docs/design/eval-methodology.md`

---

## Phase 4 — LLM-as-Judge (Days 8–10)

### Objective
Automated eval pipeline. LLM judges faithfulness, completeness, citation accuracy.

### Tasks
- [x] Implement judge prompt (Claude API or local Qwen)
- [x] Wire eval set through judge pipeline
- [x] Run baseline scores
- [x] Run scores after each retrieval config change
- [x] Track score history in `eval/results/`
- [x] Document before/after improvement evidence

---

## Phase 5 — Final Docs (Day 11)

### Objective
All 5 ADRs complete. INDEX.md current. Career artifact set finalized.

### Tasks
- [x] Complete ADR-001 through ADR-005 with eval impact data
- [x] Final SRS review and completion
- [x] Update INDEX.md with all artifacts
- [x] Write project retrospective → `docs/retrospective.md`
- [x] Verify deliverables checklist from spec

---

## Deliverables Checklist (from spec)

- [x] Working retrieval API on homelab
- [x] Chunking strategy writeup
- [x] Eval set: 20+ Q&A pairs with ground truth chunk refs
- [x] Automated eval pipeline with LLM-as-judge
- [x] ADRs for all major choices (5 required)
- [x] Before/after eval scores showing retrieval improvement

---

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |

---

## Decisions Log

| Date | Decision | Rationale | ADR |
|------|----------|-----------|-----|
| 2026-05-22 | Project scaffold created | Career path project requires full doc set from day 1 | — |
| 2026-05-22 | Embedding backend: nomic-embed-text local server | Data stays on homelab, no API cost, 768-dim | ADR-005 |
| 2026-05-22 | Chunking: hierarchical selected | Section structure maps to regulatory interpretation boundaries | ADR-002 |
| 2026-05-22 | Port 5433 for Docker pgvector | Local Postgres already on 5432 — conflict resolved | ADR-001 |
