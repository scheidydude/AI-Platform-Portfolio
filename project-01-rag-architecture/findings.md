# Findings — RAG Architecture POC

**Project:** Project 01 — RAG Architecture
**Updated:** 2026-05-22

---

## Spec Analysis

### Three Core Problems (per spec)
1. **Ingestion** — get docs in, chunked
2. **Retrieval** — find right chunks (THE hard part)
3. **Generation** — use chunks without hallucinating

Most tutorials nail #1, fumble #2, never measure #3.

### Why SEC 10-K Filings
- Public (EDGAR full-text search)
- Dense, structured, regulation-heavy
- Realistic retrieval challenge (regulatory term precision matters)

### Chunking Strategy Comparison Target
| Strategy | Approach | Best For |
|----------|----------|----------|
| Fixed-size | 512 tokens, 64 overlap | Baseline, easy to reason about |
| Semantic | Split on meaning shifts | General text |
| Hierarchical | Section + sub-chunks | Dense regulatory text (likely winner) |

### Retrieval Stack Decision (from spec)
- Dense: pgvector (native Postgres)
- Sparse: rank_bm25
- Fusion: RRF (no tuning required)
- Re-ranker: cross-encoder/ms-marco-MiniLM-L-6-v2 (CPU-viable)

### Key Tension: Embedding Model
| Option | Cost | Privacy | Notes |
|--------|------|---------|-------|
| text-embedding-3-small (API) | ~$0.02/1M tokens | Data leaves machine | Fast, no setup |
| Local llama.cpp | Free | Data stays local | Setup cost, slower |

### Citation Grounding Pattern (non-negotiable for regulated env)
- Pass chunk IDs through full pipeline
- Prompt: "cite chunk ID in [brackets] for each claim"
- If answer not in context, say so explicitly

### Eval Metrics
- Retrieval recall@K
- Faithfulness (claims supported by retrieved chunks)
- Answer relevance

### LLM Judge Output Schema
```json
{
  "faithfulness": 1-5,
  "completeness": 1-5,
  "citation_accuracy": "pass|fail",
  "reasoning": "one sentence"
}
```

---

## Research Notes

*(Add discoveries here as project progresses)*

### Phase 1 Findings
*TBD*

### Phase 2 Findings
*TBD*

### Phase 3 Findings
*TBD*

### Phase 4 Findings
*TBD*

---

## Open Questions

| Question | Status | Answer |
|----------|--------|--------|
| API vs local embeddings — which for this homelab? | open | — |
| Chunk overlap: 64 token default — validate this? | open | — |
| K value for retrieval (top-K before re-rank) | open | — |
| Claude API vs local Qwen for judge? | open | — |
