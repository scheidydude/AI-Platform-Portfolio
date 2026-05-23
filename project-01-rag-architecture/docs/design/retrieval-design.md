# Retrieval Architecture Design

**Author:** David Scheiderman
**Phase:** 2 — Retrieval
**Status:** Complete
**Date:** 2026-05-23

---

## Overview

The retrieval layer is a four-stage pipeline:

```
Query
  │
  ▼
1. Dense Retrieval (pgvector cosine)     → top-20 candidates
  │
  ▼ (parallel)
2. Sparse Retrieval (BM25Okapi)          → top-20 candidates
  │
  ▼
3. RRF Fusion                            → top-20 merged candidates
  │
  ▼
4. Cross-Encoder Re-Ranking              → top-5 final results
  │
  ▼
Ranked chunks with IDs (citation-ready)
```

Each stage is independently callable for ablation testing (see ADR-003, ADR-004 eval impact sections).

---

## Stage 1 — Dense Retrieval

**Implementation:** `search.py::dense_retrieve()`

**Mechanism:** Embed the query using nomic-embed-text (768-dim) via the OpenAI-compatible API at `http://ai.scheidy.com:8081/v1`. Execute a pgvector cosine distance scan:

```sql
SELECT c.id, c.content, c.section_title, c.parent_chunk_id,
       d.company, d.year,
       1 - (c.embedding <=> %s::vector) AS cosine_sim
FROM chunks c
JOIN documents d ON c.document_id = d.id
WHERE c.embedding IS NOT NULL
ORDER BY c.embedding <=> %s::vector
LIMIT 20
```

pgvector uses an IVFFlat index (`lists=100`) for approximate nearest neighbor. The index was built at ingestion time (`scripts/init_db.sql`).

**Parameters:**
- `k_dense = 20` — candidate pool. Overshooting is cheap; fusion narrows it.

**Corpus:** 3,332 embedded chunks across 9 10-K filings (768-dim nomic-embed-text).

---

## Stage 2 — Sparse Retrieval (BM25)

**Implementation:** `search.py::BM25Index`

**Mechanism:** BM25Okapi (rank-bm25 library) over the full embedded corpus. The index is built at server startup by fetching all chunk content from the DB and tokenizing with a simple regex tokenizer (`\b\w+\b`, lowercased). This is an in-memory index — no persistence, rebuilt on each server start (< 1s for 3,332 chunks).

**Why BM25 alongside dense:** Dense retrieval fails on exact regulatory terms (rule numbers, threshold values, act citations) when the embedding model collapses them into a generic compliance vector. BM25 catches these via exact term overlap. See ADR-003 for full rationale.

**Parameters:**
- `k_sparse = 20` — candidate pool, same as dense for symmetric fusion.

**Tokenizer:** `re.findall(r"\b\w+\b", text.lower())`. No stemming. Financial regulatory terms benefit from exact-match preservation (e.g., "Rule 17a-4" should not stem to "rule").

---

## Stage 3 — Reciprocal Rank Fusion

**Implementation:** `search.py::rrf_fuse()`

**Mechanism:** Merge dense and sparse ranked lists using RRF (Cormack, Clarke, Buettcher 2009):

```
RRF(d) = Σ 1 / (k + rank_i(d))   over all ranked lists i
```

- `k = 60` — standard constant. Cormack's experiments showed k=60 optimal across many domains; it dampens the influence of very high ranks (rank 1 contributes 1/61 ≈ 0.016) while still separating documents that appear in both lists.
- Union of both result sets — documents appearing in only one list still contribute via their single-list RRF score.
- `top_n_fused = 20` — top-20 from fusion passed to re-ranker.

**Why RRF over learned fusion:** RRF requires no training data and no hyperparameter tuning beyond k=60. For a POC corpus of 3,332 chunks with no labeled relevance data, learning a fusion weight is not justified.

---

## Stage 4 — Cross-Encoder Re-Ranking

**Implementation:** `search.py::rerank()`

**Mechanism:** `sentence-transformers` `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")`. For each of the 20 fused candidates, jointly encode (query, chunk) and produce a relevance logit. Sort descending, return top-5.

**Why cross-encoder vs. bi-encoder for re-ranking:** Cross-encoders see the full query-document pair simultaneously (attention over both) vs. bi-encoders which encode independently. The cross-encoder cannot scale to full corpus retrieval (O(n) inferences), but over 20 candidates the cost is acceptable. In practice, cross-encoders outperform bi-encoders for re-ranking tasks by a significant margin.

**Model selection:** `ms-marco-MiniLM-L-6-v2` is a well-established checkpoint trained on MS MARCO passage ranking. MiniLM-L-6 is small enough to run on CPU (< 250ms for 20 pairs on this hardware). Larger cross-encoders (L-12) would improve quality but are slower.

**Parameters:**
- `top_n_rerank = 5` — final result count passed to LLM context window.

---

## Citation Grounding

Every `ChunkResult` carries:
- `chunk_id` — stable identifier (`COMPANY_YEAR_HIER_NNNN`)
- `parent_chunk_id` — the parent section chunk (if hierarchical strategy)
- `section_title` — `Item 1A. Risk Factors.`, etc.
- `company`, `year`

The generation layer (Phase 3) will use `chunk_id` and `section_title` to construct inline citations. For multi-hop questions, `parent_chunk_id` can be used to fetch the full section context.

---

## API

**Implementation:** `src/retrieval/api.py` — Flask 3.0

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness + BM25 index readiness flag |
| `/search` | POST | Full pipeline: dense + BM25 + RRF + re-rank |
| `/search/dense` | POST | Dense-only (ablation baseline) |

**`/search` request:**
```json
{
  "query": "What are the main liquidity risks for JPMorgan Chase?",
  "top_n": 5,
  "k_dense": 20,
  "k_sparse": 20
}
```

**`/search` response:**
```json
{
  "query": "...",
  "top_n": 5,
  "results": [
    {
      "chunk_id": "JPMORGAN_2026_HIER_0021",
      "content": "...",
      "section_title": "Item 1A. Risk Factors.",
      "company": "JPMorgan_Chase",
      "year": 2026,
      "score": 5.5642,
      "parent_chunk_id": "JPMORGAN_2026_HIER_parent_0003"
    }
  ]
}
```

**Start server:**
```bash
python src/retrieval/api.py
```

BM25 index builds automatically at startup (~0.5s for 3,332 chunks). Cross-encoder model downloads from HuggingFace on first request if not cached locally.

---

## Key Parameters Summary

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `k_dense` | 20 | Provides enough dense candidates for RRF union without excessive DB scan time |
| `k_sparse` | 20 | Symmetric with dense; balanced fusion |
| `rrf_k` | 60 | Cormack 2009 standard constant; no tuning needed |
| `top_n_fused` | 20 | Cap passed to cross-encoder; 20 inferences at ~10ms each = ~200ms |
| `top_n_rerank` | 5 | Context window budget for LLM; 5 × ~300 tokens = ~1,500 tokens |

---

## Verified Behavior

Tested query: `"What are the main liquidity risks for JPMorgan Chase?"`

| Rank | Company | Section | Score |
|------|---------|---------|-------|
| 1 | JPMorgan_Chase | Item 1A. Risk Factors. | 5.56 |
| 2 | JPMorgan_Chase | Item 15 (Firmwide Risk Mgmt) | 4.19 |
| 3 | JPMorgan_Chase | Item 15 (Investment Portfolio Risk) | 3.76 |
| 4 | JPMorgan_Chase | Item 15 (Liquidity outflows) | 2.97 |
| 5 | JPMorgan_Chase | Item 1A. Risk Factors. | 2.53 |

Top result (JPMORGAN_2026_HIER_0021) leads with "Liquidity risks, including the risk that JPMorganChase's..." — correct.

---

## Known Limitations

- **BM25 in-memory:** Corpus loaded at startup. On server restart with corpus changes, BM25 auto-rebuilds. For corpora > ~1M chunks, consider a persistent sparse index (Elasticsearch, Weaviate BM25 module).
- **Wells Fargo thin:** 24 chunks from a TOC wrapper. Sparse retrieval does not compensate for missing content. Noted as known gap (see HANDOFF.md).
- **Citigroup/Morgan Stanley section titles:** `section_title = "DOCUMENT"` for these filings. Citation granularity is company+year only, not Item-level. Acceptable for Phase 2; fix section regex in Phase 3 if eval set quality demands it.
- **Cross-encoder on CPU:** ~100–300ms per 20-candidate re-rank call on homelab hardware. Acceptable for POC; production would pin to GPU or use a distilled model.
