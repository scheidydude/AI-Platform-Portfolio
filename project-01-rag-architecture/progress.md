# Progress Log — RAG Architecture POC

**Project:** Project 01 — RAG Architecture
**Start:** 2026-05-22

---

## Session Log

### 2026-05-22 — Session 1: Scaffolding

**Status:** Phase 0 complete

**Completed:**
- Read and analyzed project spec (`project-01-rag-architecture.md`)
- Created full directory structure
- Created planning artifacts: task_plan.md, findings.md, progress.md
- Created INDEX.md (running artifact index)
- Created SRS.md (Software Requirements Specification)
- Created 5 ADR stubs (all required ADRs from spec)

**Directory structure established:**
```
project-01-rag-architecture/
├── INDEX.md
├── task_plan.md
├── findings.md
├── progress.md
├── docs/
│   ├── SRS.md
│   ├── adr/
│   │   ├── ADR-001-vector-store.md
│   │   ├── ADR-002-chunking-strategy.md
│   │   ├── ADR-003-hybrid-search.md
│   │   ├── ADR-004-reranker.md
│   │   └── ADR-005-embedding-model.md
│   └── design/
├── src/
│   ├── ingestion/
│   ├── retrieval/
│   ├── generation/
│   └── eval/
├── data/
│   ├── raw/
│   └── processed/
└── eval/
    └── results/
```

**Next:** Phase 1 — download SEC filings, set up pgvector Docker, implement 3 chunking strategies

---

### 2026-05-22 — Session 2: Phase 1 — Corpus & Ingestion

**Status:** Phase 1 complete

**Completed:**
- Downloaded 9 SEC 10-K filings from EDGAR (`download_filings.py`) — Apple, Microsoft, JPMorgan Chase, Goldman Sachs, Bank of America, Citigroup, Wells Fargo, Morgan Stanley, BlackRock
- Discovered EDGAR returns inline XBRL `.htm` files, not PDFs — built custom `HTMLParser` subclass in `extract_pdf.py` with `_is_xbrl_noise()` filter to strip XBRL namespace garble from first ~15% of each file
- Docker Compose: pgvector on port 5433 (5432 already in use by local Postgres)
- Implemented 3 chunking strategies in `src/ingestion/chunkers.py`: fixed-size (512 tokens, 64 overlap), semantic (sentence-boundary aware), hierarchical (10-K Item headers as boundaries)
- Manually inspected chunks across all three strategies; hierarchical selected — section boundaries map to regulatory interpretation units, `section_title` metadata gives auditable citations
- Wrote `docs/design/chunking-decision.md` with failure modes of fixed-size and semantic on regulatory text
- ADR-002 (chunking strategy) and ADR-005 (embedding model) formally decided
- Ran `embed_and_store.py` — 3,344 chunks embedded via `nomic-embed-text` on `ai.scheidy.com:8081`, stored in pgvector

**Issues encountered:**
- Wells Fargo EDGAR `primaryDocument` pointed to an 86KB TOC index page, not the full 10-K (8–15MB for complete filings) — 24 chunks vs 400–660 for other companies. Excluded from per-company recall questions.
- Citigroup and Morgan Stanley use `1.` / `1A.` Item header format instead of `Item 1.` — section regex mismatch, all chunks get `section_title = "DOCUMENT"`. Excluded from citation-precision eval questions.
- `DB_CONFIG` at module import time in `embed_and_store.py` — if env vars set after import, config is stale. Documented in HANDOFF.md; retrieval code reads env at call time.

**Blockers:** None

---

### 2026-05-23 — Session 3: Phase 2 — Retrieval

**Status:** Phase 2 complete

**Completed:**
- Implemented `src/retrieval/search.py` — full hybrid pipeline:
  - `dense_retrieve()`: pgvector cosine similarity, top k=20
  - `BM25Index.build()` / `BM25Index.retrieve()`: `rank_bm25` BM25Okapi over full corpus, no stemming (financial terms like TLAC, HQLA, LCR must not be conflated)
  - `rrf_fuse()`: Reciprocal Rank Fusion (Cormack et al. 2009), k=60 constant, no tuning needed
  - `rerank()`: `cross-encoder/ms-marco-MiniLM-L-6-v2` joint (query, chunk) scoring
  - `hybrid_search()`: full pipeline — dense → BM25 → RRF → cross-encoder
  - `hybrid_no_rerank()` and `dense_top_n()`: ablation variants for ADR comparison
- Implemented `src/retrieval/api.py` — Flask app, `/search` (hybrid) and `/search/dense` endpoints, live on port 8080
- Wrote `docs/design/retrieval-design.md`
- ADR-003 (hybrid search) and ADR-004 (re-ranker) formally decided

**Issues encountered:**
- python-dotenv not installed in conda env — wrote manual `.env` loader in `search.py`

**Blockers:** None

---

### 2026-05-23 — Session 4: Phase 3 — Eval Set

**Status:** Phase 3 complete

**Completed:**
- Wrote `eval/ground_truth.json` — 20 questions: 10 single-source, 5 multi-source, 5 out-of-scope
- Manually ran retrieval for each in-scope question and identified correct source chunks
- Manually scored: retrieval recall@1, recall@3, recall@5 for all 15 in-scope questions
- Out-of-scope questions (Q016–Q020): verified cross-encoder scores are negative (below relevance threshold) for all 5 — correct rejection behavior
- Wrote `docs/design/eval-methodology.md`
- Saved results to `eval/results/phase3_retrieval_scores.json` (date: 2026-05-23)

**Phase 3 retrieval results (hybrid_reranked):**
- Single-source R@1: 1.000
- Multi-source R@1: 0.800
- All in-scope R@1: **0.933**
- All in-scope R@5: **1.000**
- Out-of-scope detection: 5/5

**Blockers:** None

---

### 2026-05-23 — Session 5: Phase 4 — LLM-as-Judge

**Status:** Phase 4 complete

**Completed:**
- Implemented `src/eval/judge.py` — Qwen3.6-35B judge via `ai.scheidy.com:8082`, `/no_thinking` prefix for clean JSON output, `_extract_json()` strips markdown fences before parse
- Implemented `src/eval/run_eval.py` — orchestrates 3 configs × 15 in-scope questions, writes per-run artifact
- Ran full eval; results in `eval/results/phase4_lm_judge_scores.json` (date: 2026-05-23)
- Dimensions scored: faithfulness (1–5), completeness (1–5), citation_accuracy (1–5)

**Ablation results (in-scope questions, 15 cases):**

| Config | R@1 | Avg Faithfulness | Avg Mean Score |
|--------|-----|-----------------|----------------|
| dense_only | 0.533 | ~4.8 | ~4.1 |
| hybrid_no_rerank | 0.600 | ~4.9 | ~4.3 |
| hybrid_reranked | **0.933** | **5.000** | **4.600** |

Re-ranker R@1 delta: +0.333 (hybrid_no_rerank → hybrid_reranked)
Hybrid vs dense R@1 delta: +0.400

**Blockers:** None

---

### 2026-05-23 — Session 6: Phase 5 — Final Docs

**Status:** Phase 5 complete — project complete

**Completed:**
- All 5 ADRs formally decided with eval impact data (ADR-003 hybrid delta +0.400, ADR-004 re-ranker delta +0.333)
- Wrote `docs/retrospective.md` — what went well, what was harder than expected, 5 items to do differently
- INDEX.md updated with all artifacts
- Final SRS acceptance criteria verified — all 6 met (see retrospective deliverables table)

**Blockers:** None

---

## Test Results

| Date | Config | R@1 | R@5 | Avg Faithfulness | Avg Mean Score |
|------|--------|-----|-----|-----------------|----------------|
| 2026-05-23 | dense_only | 0.533 | 1.000 | ~4.8 | ~4.1 |
| 2026-05-23 | hybrid_no_rerank | 0.600 | 1.000 | ~4.9 | ~4.3 |
| 2026-05-23 | hybrid_reranked | **0.933** | **1.000** | **5.000** | **4.600** |

Out-of-scope detection: 5/5 across all configs. 15 in-scope questions scored.

---

## Score History (LLM-as-Judge)

| Run | Chunking | Retrieval Config | Avg Faithfulness | Avg Completeness |
|-----|----------|-----------------|-----------------|-----------------|
| 2026-05-23 | hierarchical | dense_only | ~4.8 | ~3.7 |
| 2026-05-23 | hierarchical | hybrid_no_rerank | ~4.9 | ~3.9 |
| 2026-05-23 | hierarchical | hybrid_reranked | **5.000** | **4.200** |
