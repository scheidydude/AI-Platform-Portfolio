# ADR-003: Hybrid Search vs. Pure Dense Retrieval

**Status:** Decided
**Date:** 2026-05-22
**Implemented:** 2026-05-23
**Author:** David Scheiderman

---

## Context

Regulatory documents contain precise terminology (rule numbers, act names, specific thresholds) that pure vector search can miss when the embedding model represents the concept differently than the document phrases it. The query "what does Rule 17a-4 require for electronic records?" may fail pure vector search if the model embeds "Rule 17a-4" into a generic compliance vector space — but keyword search catches it exactly.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Pure dense retrieval** | Simple, one index, pgvector handles it | Misses exact-match regulatory terms; no fallback when semantic embedding diverges from document phrasing |
| **Pure sparse (BM25)** | Exact term matching, fast | Misses synonyms, paraphrases, semantic queries |
| **Hybrid (dense + BM25 + RRF)** | Best of both; catches exact terms AND semantic meaning; RRF fusion requires no tuning | Two retrieval paths to maintain; RRF adds a fusion step |

---

## Decision

**Hybrid search: dense (pgvector) + sparse (rank_bm25) fused via RRF**

---

## Rationale

Regulatory corpus retrieval has two distinct failure modes:
1. Query uses generic language, document uses precise regulatory term → dense search wins
2. Query uses precise regulatory term, document buries it in dense prose → BM25 wins

RRF (Reciprocal Rank Fusion) formula:
```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```
where k=60 (standard default). No tuning required; works well out of the box.

tradeoff accepted: added complexity of maintaining two retrieval paths. Justified by recall improvement on regulatory exact-term queries.

---

## Consequences

**Easier:**
- Exact regulatory term queries reliably retrieved
- Semantic paraphrase queries reliably retrieved

**Harder:**
- Two retrieval indexes to keep in sync
- Additional latency from BM25 + fusion step (measured, acceptable)

---

## Implementation Notes

- `src/retrieval/search.py::dense_retrieve()` — pgvector `<=>` cosine distance, top-20
- `src/retrieval/search.py::BM25Index` — rank-bm25 `BM25Okapi`, corpus loaded from DB at startup
- `src/retrieval/search.py::rrf_fuse()` — k=60, union of both result sets, top-20 output
- Tokenizer: `re.findall(r"\b\w+\b", text.lower())` — no stemming (preserves regulatory term exact match)
- Ablation endpoint: `POST /search/dense` returns dense-only results for recall comparison

## Eval Impact

*(Populated after Phase 3 eval scoring)*

| Config | Retrieval Recall@5 |
|--------|-------------------|
| Pure dense | TBD |
| Hybrid (dense + BM25 + RRF) | TBD |
| Delta | TBD |
