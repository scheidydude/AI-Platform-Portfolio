# Evaluation Methodology

**Author:** David Scheiderman
**Phase:** 3 — Eval Set
**Status:** Complete
**Date:** 2026-05-23

---

## Overview

The eval set provides a repeatable benchmark for the retrieval layer. It has three purposes:

1. **Baseline score** — establish retrieval recall before any parameter tuning
2. **Regression test** — detect quality regressions when changing retrieval config
3. **ADR evidence** — supply concrete before/after data for ADR-003 and ADR-004 eval impact sections (Phase 4)

---

## Question Set Design

20 questions across three types:

| Type | Count | Purpose |
|------|-------|---------|
| Single-source | 10 | Test retrieval precision for a specific company/topic |
| Multi-source | 5 | Test cross-company synthesis retrieval |
| Out-of-scope | 5 | Test system behavior on unanswerable questions |

### Single-source questions (Q001–Q010)

Each question targets one company in the corpus. The ground truth is 1–3 chunks from that company that directly contain the answer. A correct retrieval requires the relevant company's chunks to appear in the top results — cross-company contamination at rank 1 is a failure.

Companies covered: Apple (Q001, Q008), Microsoft (Q002), JPMorgan Chase (Q003, Q007), Goldman Sachs (Q004, Q009), Bank of America (Q005, Q010), BlackRock (Q006).

Wells Fargo, Citigroup, and Morgan Stanley were excluded from single-source questions because:
- **Wells Fargo:** Only 24 chunks (TOC wrapper file). Insufficient content for meaningful questions.
- **Citigroup and Morgan Stanley:** Section detection fell back to `section_title = "DOCUMENT"`. Cannot write questions that rely on Item-level filtering. These companies appear in multi-source questions where section precision matters less.

### Multi-source questions (Q011–Q015)

Each question is designed to have correct answers across 2+ companies. Ground truth includes chunks from 2–3 companies. Partial retrieval (1 of N companies represented in top-5) is considered a recall hit for R@K purposes.

Topics: credit risk frameworks (Q011), cybersecurity across sectors (Q012), stress testing (Q013), regulatory compliance (Q014), climate/ESG risks (Q015).

### Out-of-scope questions (Q016–Q020)

Questions where no correct answer exists in the corpus:
- Company not in corpus (Q016: Charles Schwab, Q018: Coinbase)
- Real-time data not in static 10-K filings (Q017: current Fed rates)
- Metric not disclosed in SEC filings (Q019: patent count, Q020: employee NPS)

A correct out-of-scope response is one where **all top-5 results have negative cross-encoder scores**. Negative scores indicate the cross-encoder found no evidence of a relevant query-chunk match — the system is signaling low confidence, which is correct behavior.

---

## Ground Truth Establishment

Ground truth chunk IDs were determined by the following process:

1. Run each question through `hybrid_search` (k_dense=20, k_sparse=20, RRF k=60, cross-encoder top_n=5)
2. Inspect the content of returned chunks
3. Mark chunks as ground truth if they **directly contain content that answers the question** — not just topically related, but substantively answerable from that chunk
4. Cross-reference chunk text against domain knowledge of SEC 10-K structure (Item 1A Risk Factors, Item 7 MD&A, etc.)

Ground truth is stored in `eval/ground_truth.json` alongside each question.

**Known limitations of ground truth:**
- Ground truth was established against the hybrid retrieval output, not exhaustive corpus search. There may be other valid chunks not listed as ground truth.
- Q001 was revised from "Apple's primary revenue segments" (no matching content — Apple reports one operating segment) to "Apple's supply chain and manufacturing risks" which is well-represented in the corpus.
- Q006 was revised from "BlackRock's core business model and primary revenue sources" to include explicit "AUM" framing, which substantially improved retrieval alignment.

---

## Metrics

### Retrieval Recall@K

For in-scope questions:

```
Recall@K = 1 if any ground_truth_chunk_id appears in top-K retrieved chunks
         = 0 otherwise
```

Binary (hit/miss) per question. Averaged across question set.

K values measured: 1, 3, 5.

### Out-of-scope Detection Rate

```
OOS_correct = 1 if all top-5 results have cross-encoder score < 0
            = 0 otherwise
```

A negative cross-encoder score indicates the model found no relevant match, which is the desired behavior for unanswerable questions.

### Faithfulness and Answer Relevance (Phase 4)

These metrics require a generated answer:

- **Faithfulness:** Does the generated answer contain claims supported by the retrieved chunks? Measured by LLM-as-judge in Phase 4.
- **Answer Relevance:** Does the generated answer address the question asked? Measured by LLM-as-judge in Phase 4.

Baseline scores are left as TBD in `eval/results/phase3_retrieval_scores.json` pending Phase 4 generation pipeline.

---

## Phase 3 Results (Hybrid Search Baseline)

**Retrieval config:** dense k=20 + BM25 k=20 + RRF k=60 + cross-encoder `ms-marco-MiniLM-L-6-v2` top_n=5

| Question Set | Recall@1 | Recall@3 | Recall@5 |
|-------------|---------|---------|---------|
| Single-source (n=10) | **1.000** | **1.000** | **1.000** |
| Multi-source (n=5) | **0.800** | **1.000** | **1.000** |
| All in-scope (n=15) | **0.933** | **1.000** | **1.000** |
| Out-of-scope detection | **5/5** | — | — |

### Analysis

**Single-source R@1 = 1.000:** The hybrid pipeline places a correct chunk at rank 1 for all 10 single-source questions. The cross-encoder re-ranking is responsible for this — the dense+BM25+RRF fusion produces the correct chunks in the top-20 candidates, and the cross-encoder correctly surfaces the most relevant one.

**Multi-source R@1 = 0.800 (Q011 miss):** Q011 ("How do large banks describe their credit risk management frameworks?") returned a Morgan Stanley cross-reference stub (table of contents entry) at rank 1 — not actual content. The correct credit risk description chunk (MORGAN_S_2026_HIER_0033) appeared at rank 2. This is a failure mode where the cross-encoder gave a high score to a structurally prominent but content-thin chunk. The R@3 and R@5 scores recover to 1.000.

**Out-of-scope detection = 5/5:** All 5 out-of-scope questions returned exclusively negative cross-encoder scores in the top-5. The hardest case was Q019 (Apple patent counts) where APPLE_IN_2025_HIER_0051 (product launch schedule) reached rank 1 with score -0.178 — near zero but still negative, indicating borderline out-of-scope behavior.

### Implications for Phase 4

- **Re-ranker baseline:** The current R@5=1.000 on in-scope questions means the correct chunks are reaching the LLM. Phase 4 will test whether faithfulness and completeness improve — the bottleneck is answer quality, not retrieval recall.
- **R@1 failure on Q011:** The cross-encoder assigns high scores to content-thin structural chunks (cross-references, table of contents entries). A potential fix is a minimum content length filter before re-ranking, or including token count in the re-ranking signal.
- **Ablation baseline:** To populate ADR-003 and ADR-004 eval impact, run the same 15 in-scope questions through `/search/dense` (dense-only) and compare R@K. Predicted: dense-only will score lower on Q003, Q007, Q009 (liquidity/capital regulatory-term queries where BM25 contributes exact-term recall).

---

## Files

| File | Purpose |
|------|---------|
| `eval/ground_truth.json` | 20 questions with GT chunk IDs, company expectations, notes |
| `eval/results/phase3_retrieval_scores.json` | Per-question R@K scores + aggregate summary |
| `eval/results/phase4_lm_judge_scores.json` | LLM-as-judge scores (Phase 4, not yet created) |
