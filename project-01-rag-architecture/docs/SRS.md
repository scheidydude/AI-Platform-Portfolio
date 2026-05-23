# Software Requirements Specification
## Project 01 — RAG Architecture POC

**Version:** 1.0 (final)
**Author:** David Scheiderman
**Date:** 2026-05-22
**Updated:** 2026-05-23
**Status:** Complete

---

## 1. Purpose

Build a production-quality RAG (Retrieval-Augmented Generation) pipeline over SEC 10-K regulatory filings. Demonstrate retrieval quality engineering, not just ingestion. Serve as a career artifact proving AI architecture competency.

---

## 2. Scope

### In Scope
- HTML ingestion of 9 SEC 10-K filings from EDGAR (inline XBRL `.htm` format)
- Three chunking strategies implemented and compared
- Hybrid retrieval (dense vector + BM25 sparse + RRF fusion)
- Cross-encoder re-ranking
- Citation grounding (every answer references source chunk IDs)
- Manual eval set: 20+ Q&A pairs with ground truth
- Automated LLM-as-judge eval pipeline
- Architecture Decision Records for all major choices
- Career documentation artifact set

### Out of Scope
- Real-time document ingestion (static corpus only)
- Multi-user / auth / access control
- Production deployment (homelab POC only)
- Fine-tuning any model

---

## 3. Stakeholders

| Role | Person | Interest |
|------|--------|----------|
| Developer / AI Architect candidate | David Scheiderman | Build + document |
| Hiring reviewers (future) | TBD | Review artifact set for competency evidence |

---

## 4. Functional Requirements

### FR-01: Corpus Ingestion
- System SHALL ingest HTML documents from SEC EDGAR (inline XBRL `.htm` format)
- System SHALL extract text from HTML with XBRL noise filtering (custom `HTMLParser` subclass)
- System SHALL support 3 chunking strategies (fixed-size, semantic, hierarchical)
- System SHALL store chunks with metadata (source file, section title, chunk ID, strategy, parent_chunk_id)

### FR-02: Embedding
- System SHALL generate vector embeddings for all chunks
- System SHALL use local nomic-embed-text (768-dim) via OpenAI-compatible API at `ai.scheidy.com:8081`
- System SHALL store embeddings in pgvector (`vector(768)`, IVFFlat index)

### FR-03: Retrieval
- System SHALL implement dense vector similarity search (pgvector)
- System SHALL implement BM25 sparse keyword search (`rank_bm25`)
- System SHALL fuse dense and sparse results using Reciprocal Rank Fusion (RRF)
- System SHALL re-rank top-K results using cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- System SHALL return chunk IDs with every retrieved chunk

### FR-04: Generation
- System SHALL pass retrieved chunks with IDs to LLM context
- System SHALL prompt LLM to cite company name and section for every claim
- System SHALL prompt LLM to explicitly state when answer cannot be found in context
- System SHALL use Qwen3.6-35B via local homelab server (`ai.scheidy.com:8082`) as LLM backend

### FR-05: Evaluation
- System SHALL support a ground truth eval set (JSON format)
- System SHALL measure retrieval recall@K against ground truth
- System SHALL run automated LLM-as-judge scoring (faithfulness, completeness, citation accuracy)
- System SHALL persist eval results for before/after comparison

---

## 5. Non-Functional Requirements

### NFR-01: Performance
- Retrieval latency: < 2s end-to-end on NucBox-class hardware
- Re-ranker: must run on CPU (no GPU required)

### NFR-02: Observability
- All retrieval results include chunk source metadata
- Eval scores tracked over time (config change → score delta visible)

### NFR-03: Portability
- Full stack runs in Docker Compose (Postgres + pgvector)
- No cloud dependencies required (local model path supported)

### NFR-04: Documentation
- Every major architectural decision has an ADR
- Written rationale exists for chunking strategy selection
- Eval methodology documented

---

## 6. System Architecture Overview

```
SEC EDGAR HTML (.htm, inline XBRL)
      │
      ▼
 HTML Extraction (custom HTMLParser, XBRL noise filter)
      │
      ▼
 Hierarchical Chunking (parent sections + sub-chunks)
      │
      ▼
 Embedding (nomic-embed-text, 768-dim, ai.scheidy.com:8081)
      │
      ▼
 pgvector (Postgres, Docker, port 5433)
      │
   ┌──┴──────────────┐
   │                 │
Dense Search      BM25 Search
(pgvector IVFFlat) (rank_bm25, in-memory)
   │                 │
   └──────┬──────────┘
          │
        RRF Fusion (k=60)
          │
          ▼
    Cross-Encoder Re-rank
    (ms-marco-MiniLM-L-6-v2, CPU)
          │
          ▼
    LLM Generation (Qwen3.6-35B, ai.scheidy.com:8082)
    [with company + section citation grounding]
          │
          ▼
       Answer + Citations
```

---

## 7. Tech Stack

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| HTML extraction | Custom `HTMLParser` subclass | XBRL noise filter built-in |
| Chunking | Python — custom implementations | fixed, semantic, hierarchical (hierarchical deployed) |
| Vector store | Postgres + pgvector | Docker, port 5433 |
| Embeddings | nomic-embed-text local server | 768-dim, `ai.scheidy.com:8081` |
| Sparse search | rank_bm25 0.2.2 | BM25Okapi, in-memory corpus |
| Re-ranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | sentence-transformers, CPU |
| LLM (generation + judge) | Qwen3.6-35B-A3B-MXFP4 | `ai.scheidy.com:8082`, OpenAI-compatible |
| Retrieval API | Flask 3.0 | `src/retrieval/api.py` |
| Infra | Docker Compose | pgvector/pgvector:pg16 |
| Language | Python 3.9.7 | miniforge conda; `typing` module required (no 3.10+ union syntax) |

---

## 8. Document References

| Document | Location | Status |
|----------|----------|--------|
| ADR-001: Vector Store | `docs/adr/ADR-001-vector-store.md` | Decided |
| ADR-002: Chunking Strategy | `docs/adr/ADR-002-chunking-strategy.md` | Decided |
| ADR-003: Hybrid Search | `docs/adr/ADR-003-hybrid-search.md` | Decided |
| ADR-004: Re-ranker | `docs/adr/ADR-004-reranker.md` | Decided |
| ADR-005: Embedding Model | `docs/adr/ADR-005-embedding-model.md` | Decided |
| Chunking Decision | `docs/design/chunking-decision.md` | Complete |
| Retrieval Design | `docs/design/retrieval-design.md` | Complete |
| Eval Methodology | `docs/design/eval-methodology.md` | Complete |
| Retrospective | `docs/retrospective.md` | Complete |

---

## 9. Acceptance Criteria

| Criterion | Measure |
|-----------|---------|
| Working retrieval API | Returns answers with citations for any query |
| Chunking decision documented | Written rationale, 3 strategies compared |
| Eval set complete | 20+ Q&A pairs, manual ground truth chunk refs |
| Automated eval running | LLM judge scores all 20+ pairs after each config change |
| ADRs complete | All 5 ADRs with eval impact data filled in |
| Before/after improvement | Score delta documented for at least one retrieval config change |
