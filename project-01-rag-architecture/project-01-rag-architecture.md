# Project 1 — RAG Architecture
**Skill area:** RAG architecture  
**Format:** Homelab build  
**Estimated duration:** 11 days

---

## Overview

Design and build a RAG pipeline over a static corpus of policy and compliance documents. Use publicly available SEC 10-K filings or FINRA rulebooks as your corpus. The challenge is retrieval quality, not just ingestion — most RAG tutorials nail the easy part and skip the hard part entirely.

---

## The mental model

RAG has three distinct problems that most tutorials collapse into one:

- **Ingestion** — getting documents in and chunked
- **Retrieval** — finding the right chunks for a given query
- **Generation** — using retrieved chunks correctly without hallucinating

Most people nail ingestion, fumble retrieval, and never measure any of it. This project is specifically designed to force you to get retrieval right.

---

## Phase 1 — Corpus & ingestion (Days 1–2)

### Corpus selection

Use SEC 10-K filings from EDGAR full-text search. They are public, dense, structured, and regulation-heavy enough to be realistic. Grab 10–15 filings as PDFs.

### Ingestion stack

| Component | Tool | Notes |
|---|---|---|
| PDF extraction | `pdfplumber` | Handles tables better than pypdf |
| Chunking | Raw Python or LangChain | Don't abstract too much — you want visibility |
| Vector store | `pgvector` on Postgres | Trivial to spin up in Docker |
| Embeddings | `text-embedding-3-small` or local llama.cpp model | Cost vs. privacy tradeoff worth documenting |

### Chunking strategies — try all three and compare

1. **Fixed-size with overlap** — 512 tokens, 64 token overlap. Baseline. Simple to implement, easy to reason about.
2. **Semantic chunking** — split on meaning shifts rather than token count. Libraries like `semantic-chunkers` or LangChain's `SemanticChunker` handle this.
3. **Hierarchical chunking** — store full sections AND sub-chunks. Index sub-chunks for retrieval but pass the parent section as context to the LLM. Best for dense regulatory text.

> **Deliverable for this phase:** A written chunking strategy decision — why you chose your final approach. This writeup is the artifact, not just the code.

---

## Phase 2 — Retrieval (Days 3–5)

This is where the project earns its keep. Naive vector search is not sufficient for a regulated corpus.

### Build hybrid search

Combine dense retrieval (vector similarity) with sparse retrieval (BM25 keyword search):

- **Dense:** pgvector handles this natively
- **Sparse:** `rank_bm25` Python library or `sqlite-fts5` for lightweight keyword search
- **Fusion:** Reciprocal Rank Fusion (RRF) — simple formula, works well, no tuning required

**Why this matters:** A query like *"what does Rule 17a-4 require for electronic records?"* can miss on pure vector search if the model embeds the concept differently than the document phrases it. Keyword search catches literal terms; vector search catches semantic intent. You need both.

### Add a re-ranker

After retrieval, score the top-K chunks with a cross-encoder re-ranker before passing them to the LLM.

- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` from HuggingFace
- Runs on CPU, fine on a NucBox-class machine
- This single step typically improves answer quality more than any other retrieval tweak

### Build in citation grounding

Every answer the LLM produces must reference the specific chunk(s) it used. Pass chunk IDs through the full pipeline and prompt the model to cite them. This is non-negotiable in regulated environments and something most RAG demos skip entirely.

**Example prompt pattern:**
```
Answer the following question using only the provided context chunks.
For each claim in your answer, cite the chunk ID it came from in [brackets].
If the answer cannot be found in the context, say so explicitly.

Context:
[CHUNK_001]: {text}
[CHUNK_002]: {text}
...

Question: {question}
```

---

## Phase 3 — Eval set (Days 6–7)

Build your ground truth before you touch generation quality. 20 Q&A pairs minimum:

| Category | Count | Purpose |
|---|---|---|
| Single-source questions | 10 | Clear answer exists in one chunk |
| Multi-source questions | 5 | Requires synthesizing across chunks |
| Out-of-scope questions | 5 | Corpus cannot answer — tests hallucination |

For each question, manually identify the correct source chunk(s). This is your ground truth.

### Metrics to track

- **Retrieval recall@K** — did the correct chunk appear in the top K results?
- **Faithfulness** — does the answer contain only claims supported by retrieved chunks?
- **Answer relevance** — does the answer actually address the question?

Score manually in this phase. Automate in Phase 4.

---

## Phase 4 — LLM-as-judge scoring (Days 8–10)

Wire up an automated eval judge. Prompt Claude or a local model to score each answer on a rubric.

### Judge prompt template

```
You are an evaluator for a RAG system over regulatory documents.

Given:
- Question: {question}
- Retrieved chunks: {chunks}
- System answer: {answer}
- Ground truth answer: {ground_truth}

Score the answer on the following dimensions and return JSON only:
{
  "faithfulness": <1-5>,        // Only uses information from retrieved chunks
  "completeness": <1-5>,        // Fully addresses the question
  "citation_accuracy": <pass|fail>,  // Cited chunks are actually relevant
  "reasoning": "<one sentence explanation>"
}
```

### Automation

Run your full eval set through this judge after every change to:
- Chunking strategy or parameters
- Retrieval configuration (K, re-ranker threshold)
- System prompt or generation parameters

Track scores over time. You will immediately see which changes actually help.

---

## Phase 5 — Architecture decision record (Day 11)

Document the decisions you made and why. This ADR is what you present in an AI Architect conversation. It proves you understand tradeoffs, not just implementation.

### ADR template

```markdown
## Decision: [topic]

### Context
What problem were you solving?

### Options considered
| Option | Pros | Cons |
|---|---|---|
| ... | ... | ... |

### Decision
What did you choose and why?

### Consequences
What does this make easier or harder?

### Eval impact
What did the scores look like before and after?
```

### Required ADRs for this project

1. Vector store selection (pgvector vs. Qdrant vs. Pinecone)
2. Chunking strategy selection and parameters
3. Hybrid search vs. pure dense retrieval
4. Re-ranker: include or skip?
5. Embedding model: API vs. local

---

## Full stack summary

| Layer | Choice | Rationale |
|---|---|---|
| Storage | Postgres + pgvector | Familiar Docker ops, no new infra |
| Embeddings | `text-embedding-3-small` or local | Document the cost/privacy tradeoff |
| Sparse search | `rank_bm25` | Lightweight, no extra service |
| Re-ranker | HuggingFace cross-encoder | Runs on NucBox, significant quality lift |
| LLM | Claude API or local Qwen | Swap and compare — that's the point |
| Eval | LLM-as-judge + manual ground truth | Feeds directly into Project 4 |

---

## Deliverables checklist

- [ ] Working retrieval API running on homelab
- [ ] Chunking strategy writeup (why you chose it)
- [ ] Eval set: 20+ Q&A pairs with ground truth chunk references
- [ ] Automated eval pipeline with LLM-as-judge scoring
- [ ] Architecture decision records for all major choices
- [ ] Before/after eval scores showing impact of retrieval improvements

---

## Where to start right now

Spin up pgvector locally, grab 3 SEC filings, and write a chunking script that produces chunks you can actually read and inspect. Don't automate anything yet — manually look at 20–30 chunks and ask yourself *"would this chunk answer a question about X?"* That intuition is what the rest of the project is built on.
