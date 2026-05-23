# ADR-002: Chunking Strategy

**Status:** Decided
**Date:** 2026-05-22
**Author:** David Scheiderman

---

## Context

10-K filings are dense regulatory text with mixed structure: narrative MD&A sections, financial tables, footnotes, legal boilerplate, risk factors. Chunk quality directly determines retrieval quality — bad chunks mean bad answers regardless of retrieval sophistication.

Three strategies were implemented and compared. Manual inspection of 20–30 chunks per strategy informed this decision.

---

## Options Considered

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **Fixed-size with overlap** | 512 tokens, 64 token overlap | Simple, predictable, easy to debug | Cuts mid-sentence, mid-table; no semantic awareness |
| **Semantic chunking** | Split on meaning shifts (LangChain SemanticChunker) | Preserves semantic units | Chunk sizes vary wildly; tables often mangled |
| **Hierarchical chunking** | Store full sections + sub-chunks; retrieve sub-chunks, pass parent as context | Best for regulatory text; preserves context; citation still granular | More complex; higher storage; requires parent-child metadata |

---

## Decision

**Hierarchical chunking** — sub-chunks (512 tokens, 64 overlap) indexed for retrieval; parent sections stored as context holders passed to LLM at generation time.

---

## Rationale

- 10-K Item structure is semantically correct chunking boundary: Item 1A = Risk Factors, Item 7 = MD&A
- Sub-chunk retrieval (precise) + parent section context (complete) is the right model for regulated text
- Fixed-size mid-concept cuts create incomplete disclosures — high faithfulness, low completeness
- Semantic chunker produces 3–6 token orphan chunks from financial tables (noise in index)
- Citation grounding is more auditable with section-level metadata on every chunk

See `docs/design/chunking-decision.md` for full rationale, data, and manual inspection notes.

---

## Consequences

**Easier:**
- Citation format includes section title (auditable: "Item 1A. Risk Factors")
- LLM receives both precise retrieved passage and full section context
- Section boundary = retrieval precision boundary = regulatory interpretation boundary

**Harder:**
- More complex storage: parent_chunk_id, is_parent flag, two-tier metadata
- Parent sections can be 5000–15000 tokens (JPMorgan Item 7 MD&A) — not embedded, just context
- Section regex detection edge cases in non-standard Item header formatting

---

## Eval Impact

*(Populated after Phase 3 eval set scoring)*

| Strategy | Retrieval Recall@5 | Faithfulness (avg) |
|----------|-------------------|-------------------|
| Fixed-size | TBD | TBD |
| Semantic | TBD | TBD |
| Hierarchical | TBD | TBD |
