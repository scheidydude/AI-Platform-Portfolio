# ADR-005: Embedding Model — API vs. Local

**Status:** Decided
**Date:** 2026-05-22
**Author:** David Scheiderman

---

## Context

Embeddings must be generated at ingestion time (for all chunks) and at query time (for each user query). Two viable paths: OpenAI API (`text-embedding-3-small`) or a locally-running model via llama.cpp / sentence-transformers. The choice involves cost, privacy, latency, and setup complexity tradeoffs.

This is explicitly documented as a tradeoff worth capturing per the project spec.

---

## Options Considered

| Option | Cost | Privacy | Latency | Setup |
|--------|------|---------|---------|-------|
| **text-embedding-3-small (OpenAI API)** | ~$0.02/1M tokens | Data sent to OpenAI | Low (API call) | Trivial (API key) |
| **Local sentence-transformers** | Free | Data stays on machine | Medium (CPU inference) | Moderate |
| **Local llama.cpp model** | Free | Data stays on machine | Medium-high (CPU) | High |

---

## Decision

**Local nomic-embed-text via homelab inference server**
- Server: `http://ai.scheidy.com:8081/v1` (OpenAI-compatible API)
- Model: `nomic-embed-text`
- Dimensions: 768
- Backend: llama.cpp or equivalent inference server

---

## Rationale

1. **Homelab-first principle:** Existing inference server already running. Zero additional cost or setup.
2. **OpenAI-compatible API:** The local server exposes `/v1/embeddings` — same interface as OpenAI. Switching to OpenAI `text-embedding-3-small` in future requires only changing `base_url` and `model` env vars, not code.
3. **No data egress:** SEC 10-K filings are public, but homelab practice should default to local to build the right habits.
4. **nomic-embed-text quality:** Strong general-purpose embedding model. MTEB leaderboard competitive at 768 dims. Appropriate for regulatory text retrieval.
5. **768 vs 1536 dims:** Lower dimension = faster ANN search, smaller index. Quality tradeoff acceptable for this corpus size (3,332 chunks).

---

## Consequences

**Easier:**
- No API key management
- No per-token cost at query time
- Model consistent across ingestion and retrieval (same server, same weights)

**Harder:**
- Inference server must be running for both ingestion and queries
- If homelab server is down, retrieval fails (no fallback configured)
- Switching models requires full re-ingestion (all 3,332 chunks need new embeddings)

---

## Eval Impact

**Measured:** Phases 3–4. Only `nomic-embed-text` was tested — switching models requires full re-ingestion (3,332 chunks × new embedding dimensions), which was out of scope for this POC phase.

| Model | R@5 (hybrid pipeline) | Avg Faithfulness | Notes |
|-------|----------------------|-----------------|-------|
| text-embedding-3-small (OpenAI) | not tested | not tested | Would require ANTHROPIC/OpenAI key + re-ingestion |
| **nomic-embed-text local (768-dim)** | **1.000** | **5.000** | Deployed; 3,332 chunks embedded |

**Verdict:** nomic-embed-text delivered strong retrieval quality — R@5=1.000 with hybrid pipeline, avg faithfulness 5.000/5. Comparison against text-embedding-3-small was not performed. Given the excellent results, re-ingestion to test an alternative model is low priority. Decision confirmed for this corpus.
