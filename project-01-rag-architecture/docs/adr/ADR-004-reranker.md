# ADR-004: Re-ranker — Include or Skip?

**Status:** Decided
**Date:** 2026-05-22
**Implemented:** 2026-05-23
**Author:** David Scheiderman

---

## Context

After hybrid retrieval returns top-K chunks, we can optionally pass them through a cross-encoder re-ranker before sending to the LLM. Cross-encoders jointly encode the query + chunk (not independently like bi-encoders), giving higher-quality relevance scores — at the cost of additional latency and compute.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Skip re-ranker** | Simpler pipeline, lower latency | Top-K from retrieval may include marginally relevant chunks that degrade LLM answer quality |
| **Cross-encoder re-ranker** | Significantly improves answer quality per spec ("this single step typically improves answer quality more than any other retrieval tweak"); runs on CPU | Additional step; ~100–300ms on NucBox; adds HuggingFace dependency |

---

## Decision

**Include cross-encoder re-ranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`**

---

## Rationale

Per project spec guidance: the re-ranker delivers the highest per-step quality improvement in the pipeline. The model runs on CPU — viable on homelab hardware. The latency cost is acceptable for a POC retrieval API.

The ms-marco-MiniLM-L-6-v2 model is a well-established cross-encoder trained on MS MARCO passage ranking — appropriate for the chunk relevance scoring task.

---

## Consequences

**Easier:**
- LLM receives higher-quality, better-ranked context
- Faithfulness scores improve (fewer irrelevant chunks in context)

**Harder:**
- Pipeline has one more step (diagnose re-ranker as failure point if scores drop)
- HuggingFace model download required on first run

---

## Implementation Notes

- `src/retrieval/search.py::rerank()` — `sentence-transformers` `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")`
- Input: top-20 RRF-fused candidates; output: top-5 re-ranked by cross-encoder logit
- Model loaded lazily on first request; cached module-level for subsequent calls
- Inference: ~100–300ms for 20 pairs on CPU (homelab NucBox)
- Ablation: call `rrf_fuse()` + skip `rerank()` to compare against re-ranked baseline

## Eval Impact

**Measured:** Phase 4, 2026-05-23 — 15 in-scope questions, Qwen3.6-35B judge, `eval/results/phase4_lm_judge_scores.json`

| Config | R@1 | R@5 | Avg Faithfulness | Avg Completeness | Avg Mean Score |
|--------|-----|-----|-----------------|-----------------|----------------|
| Hybrid without re-ranker (RRF top-5) | 0.600 | 0.867 | 4.933 | 3.867 | 4.422 |
| Hybrid with re-ranker (cross-encoder) | **0.933** | **1.000** | **5.000** | **4.200** | **4.600** |
| Delta | **+0.333** | **+0.133** | +0.067 | +0.333 | +0.178 |

**Key observations:**
- R@1 improvement of +55.5% relative — the cross-encoder promotes the most relevant chunk to rank 1, not just into top-5
- Completeness improves +0.333 — LLM answers are more thorough when the best chunk is at rank 1 (LLM attends more to earlier context)
- Faithfulness near ceiling (4.933 → 5.000) in both configs — RRF already excludes most irrelevant chunks; re-ranker polishes ordering

**Verdict:** Re-ranker delivers the spec-predicted quality improvement. The R@1 gain (+0.333) is the primary signal — correct chunk at position 1 directly improves answer completeness. Decision confirmed.
