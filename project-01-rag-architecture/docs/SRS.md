# Software Requirements Specification
## Project 01 — RAG Architecture POC

**Version:** 0.1 (draft)
**Author:** David Scheiderman
**Date:** 2026-05-22
**Status:** In Progress

---

## 1. Purpose

Build a production-quality RAG (Retrieval-Augmented Generation) pipeline over SEC 10-K regulatory filings. Demonstrate retrieval quality engineering, not just ingestion. Serve as a career artifact proving AI architecture competency.

---

## 2. Scope

### In Scope
- PDF ingestion of 10–15 SEC 10-K filings from EDGAR
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
- System SHALL ingest PDF documents from SEC EDGAR
- System SHALL extract text and tables from PDFs (`pdfplumber`)
- System SHALL support 3 chunking strategies (fixed-size, semantic, hierarchical)
- System SHALL store chunks with metadata (source file, page, chunk ID, strategy)

### FR-02: Embedding
- System SHALL generate vector embeddings for all chunks
- System SHALL support both API-based (`text-embedding-3-small`) and local embedding models
- System SHALL store embeddings in pgvector

### FR-03: Retrieval
- System SHALL implement dense vector similarity search (pgvector)
- System SHALL implement BM25 sparse keyword search (`rank_bm25`)
- System SHALL fuse dense and sparse results using Reciprocal Rank Fusion (RRF)
- System SHALL re-rank top-K results using cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- System SHALL return chunk IDs with every retrieved chunk

### FR-04: Generation
- System SHALL pass retrieved chunks with IDs to LLM context
- System SHALL prompt LLM to cite specific chunk IDs for every claim
- System SHALL prompt LLM to explicitly state when answer cannot be found in context
- System SHALL support Claude API and local Qwen as interchangeable LLM backends

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
SEC EDGAR PDFs
      │
      ▼
 PDF Extraction (pdfplumber)
      │
      ▼
 Chunking (fixed / semantic / hierarchical)
      │
      ▼
 Embedding (text-embedding-3-small OR local)
      │
      ▼
 pgvector (Postgres)
      │
   ┌──┴──────────────┐
   │                 │
Dense Search      BM25 Search
(pgvector)       (rank_bm25)
   │                 │
   └──────┬──────────┘
          │
        RRF Fusion
          │
          ▼
    Cross-Encoder Re-rank
          │
          ▼
    LLM Generation (Claude / Qwen)
    [with citation grounding]
          │
          ▼
       Answer + Citations
```

---

## 7. Tech Stack

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| PDF extraction | pdfplumber | Latest |
| Chunking | Python + LangChain SemanticChunker | - |
| Vector store | Postgres + pgvector | Docker |
| Embeddings | text-embedding-3-small OR local | TBD (see ADR-005) |
| Sparse search | rank_bm25 | Python library |
| Re-ranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | HuggingFace, CPU |
| LLM | Claude API OR local Qwen | Swappable (see ADR) |
| Eval judge | Claude API OR local | LLM-as-judge pattern |
| Infra | Docker Compose | Local homelab |
| Language | Python 3.11+ | - |

---

## 8. Document References

| Document | Location | Status |
|----------|----------|--------|
| Project Spec | `../project-01-rag-architecture.md` | Final |
| ADR-001: Vector Store | `docs/adr/ADR-001-vector-store.md` | Stub |
| ADR-002: Chunking Strategy | `docs/adr/ADR-002-chunking-strategy.md` | Stub |
| ADR-003: Hybrid Search | `docs/adr/ADR-003-hybrid-search.md` | Stub |
| ADR-004: Re-ranker | `docs/adr/ADR-004-reranker.md` | Stub |
| ADR-005: Embedding Model | `docs/adr/ADR-005-embedding-model.md` | Stub |
| Chunking Decision | `docs/design/chunking-decision.md` | Not started |
| Retrieval Design | `docs/design/retrieval-design.md` | Not started |
| Eval Methodology | `docs/design/eval-methodology.md` | Not started |
| Retrospective | `docs/retrospective.md` | Not started |

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
