# Chunking Strategy Decision

**Author:** David Scheiderman
**Date:** 2026-05-22
**Status:** Complete
**Phase:** Phase 1 — Corpus & Ingestion

---

## The Question

Which chunking strategy produces chunks that best answer isolated questions from dense regulatory 10-K filings?

---

## What We Tested

Three strategies implemented against 9 SEC 10-K filings from EDGAR (Apple, JPMorgan Chase, Goldman Sachs, Bank of America, Citigroup, Wells Fargo, Morgan Stanley, BlackRock, Microsoft):

| Strategy | Description | Parameters |
|----------|-------------|-----------|
| Fixed-size | Split on token count with overlap | 512 tokens, 64-token overlap |
| Semantic | Split on cosine similarity drops between sentences | 90th percentile breakpoint, 100–800 token bounds |
| Hierarchical | Section-level parents + sub-chunks | Sub-chunk: 512 tokens, 64 overlap |

---

## Observed Metrics

**Chunk count and size distribution across 3 representative filings:**

| Doc | Strategy | Chunk Count | Min | Max | Avg Tokens |
|-----|----------|-------------|-----|-----|-----------|
| Apple (69 pages) | fixed | 133 | 27 | 507 | 350 |
| Apple (69 pages) | semantic | 121 | 3 | 798 | 370 |
| Apple (69 pages) | hier (subs) | 111 | 2 | 511 | 405 |
| JPMorgan (391 pages) | fixed | 813 | 28 | 509 | 348 |
| JPMorgan (391 pages) | semantic | 630 | 6 | 797 | 429 |
| JPMorgan (391 pages) | hier (subs) | 635 | 2 | 509 | 454 |
| Goldman (364 pages) | fixed | 750 | 15 | 510 | 332 |
| Goldman (364 pages) | semantic | 629 | 5 | 797 | 380 |
| Goldman (364 pages) | hier (subs) | 571 | 5 | 511 | 440 |

---

## Manual Inspection Findings

### Fixed-size chunks
- **Strengths:** Perfectly predictable size, simple to debug, consistent avg ~350 tokens
- **Weaknesses:** Cuts mid-sentence, mid-table, and mid-risk-factor list. Chunks 27 and 28 from JPMorgan Risk Factors were split across the boundary of a key disclosure — a retrieval hit on chunk 27 would miss the conclusion in chunk 28.
- **Representative bad chunk:** A chunk begins mid-sentence ("...required under Rule 15c3-3 of the Exchange Act. JPMorganChase could face...") with no context for what the previous sentence established.
- **Representative good chunk:** Cover page, table of contents, and preamble sections chunk cleanly at 350 tokens with natural paragraph breaks.

### Semantic chunks
- **Strengths:** Respects sentence boundaries. Average chunks are slightly larger (370–429 tokens) with more complete thoughts.
- **Weaknesses:** Produces very small chunks (min 3–6 tokens) when sentence-level similarity is uniform for long stretches — financial tables produce a flat similarity landscape causing no breakpoints for hundreds of tokens, then a burst of tiny chunks at narrative transitions. Chunk size variance is the highest of the three strategies.
- **Representative bad chunk:** A 5-token chunk: "as of December 31, 2025." — captured as a standalone semantic unit because the preceding table had low similarity to the paragraph that followed.
- **Representative good chunk:** The MD&A discussion of credit loss reserves — 720 tokens, complete narrative arc from problem statement to resolution.

### Hierarchical chunks
- **Strengths:** Section boundaries are meaningful and correct. Sub-chunks inherit section context. Retrieved sub-chunk of 480 tokens from Risk Factors can be paired with the full Risk Factors parent section for LLM context — the LLM sees both the exact passage AND the surrounding regulatory framework.
- **Weaknesses:** Some very short sub-chunks (min 2 tokens) in sections like "Unresolved Staff Comments" (typically "None."). Slightly higher chunk count than semantic for large docs. More complex to implement and store (parent-child metadata).
- **Representative good chunk:** Sub-chunk from `Item 1A. Risk Factors.` section — 492 tokens covering liquidity risk factors with full context from the parent section available for generation.
- **For regulatory text specifically:** 10-K Item structure (Item 1 Business, Item 1A Risk Factors, Item 7 MD&A) maps naturally to the hierarchical model. Questions about risk factors should retrieve from Item 1A, MD&A questions from Item 7. The section boundary = the right context boundary.

---

## Decision

**Hierarchical chunking** — sub-chunks indexed for retrieval, parent sections passed to LLM for generation.

---

## Rationale

1. **Regulatory text has natural, meaningful structure.** 10-K filings are organized by SEC-mandated Items (1, 1A, 1B, 2, 3...). These boundaries are semantically correct — a question about risk factors belongs in Item 1A, not wherever a 512-token window happens to land.

2. **The two-stage retrieval-generation split is the right model for this corpus.** Retrieve precisely (sub-chunk, 400–500 tokens) but provide context generously (full parent section, potentially 5000+ tokens for MD&A). Fixed-size has no concept of "context beyond the retrieved chunk." Hierarchical makes context retrieval explicit.

3. **Citation grounding benefits from section structure.** When every sub-chunk carries `section_title` and `parent_chunk_id`, citations are interpretable: "[JPMORGAN_2026_HIER_0022, Item 1A. Risk Factors.]" is more auditable than "[JPMORGAN_2026_FIXE_0813]".

4. **Fixed-size mid-concept cuts are a liability in regulated environments.** An LLM that receives only half a risk factor disclosure may produce a misleadingly incomplete answer with high faithfulness score (everything it said was in the chunk) but low completeness score (the full picture required the adjacent chunk). Hierarchical avoids this by sizing sub-chunks within section boundaries.

5. **Semantic chunking's tiny-chunk problem is worse for financial tables.** 10-Ks contain dense financial statement tables. The sentence-similarity algorithm produces uniform low similarity through numeric rows and then clusters breakpoints at narrative transitions, creating 3–6 token orphan chunks from table footer text. These are noise in the index.

---

## Tradeoffs Accepted

| Tradeoff | Decision |
|----------|---------|
| More complex to implement | Accepted — parent-child metadata is manageable |
| Parent sections can be very long (Item 7 MD&A = 10K+ tokens) | Mitigated — LLM receives sub-chunk for citation, parent section for context; sub-chunk is what's cited |
| Some sub-chunks are very short (2–5 tokens) in "None" sections | Accepted — these are rare and can be filtered at retrieval time by token count threshold |
| Section detection relies on regex — may miss non-standard Item headers | Mitigated — tested across 9 documents, 18 sections consistently detected; edge cases noted |

---

## Impact on ADR-002

See `docs/adr/ADR-002-chunking-strategy.md` for the formal decision record. Eval impact scores to be added in Phase 3 after retrieval eval set is scored.
