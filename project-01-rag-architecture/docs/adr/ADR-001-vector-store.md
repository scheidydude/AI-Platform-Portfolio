# ADR-001: Vector Store Selection

**Status:** Decided
**Finalized:** 2026-05-23
**Date:** 2026-05-22
**Author:** David Scheiderman

---

## Context

RAG pipeline requires persistent vector storage for chunk embeddings. Need to choose between managed cloud solutions, purpose-built vector DBs, and Postgres extensions. Homelab environment (NucBox-class), static corpus, no multi-tenancy required.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **pgvector (Postgres)** | Familiar ops, Docker Compose trivial, SQL for metadata filtering, no new infra, ACID guarantees | Not purpose-built for vectors, performance ceiling vs. ANN-native stores |
| **Qdrant** | Purpose-built ANN, fast, rich filtering, good Python client | New infra to learn and maintain, overkill for static corpus |
| **Pinecone** | Managed, no ops | Paid, data leaves machine, vendor lock-in, privacy concern for regulatory docs |
| **ChromaDB** | Embedded, simple dev experience | Less production-ready, limited metadata filtering |

---

## Decision

**pgvector on Postgres (Docker)**

---

## Rationale

- Homelab constraint: Docker Compose already required for Postgres; adding pgvector costs zero extra infra
- Static corpus of 10–15 docs — performance ceiling of pgvector not reached
- SQL-native metadata filtering (source file, chunk ID, page number) without extra query layer
- Familiar ops model; no new failure modes to debug while learning RAG concepts
- Tradeoff acknowledged: would evaluate Qdrant for corpora > 100K chunks

---

## Consequences

**Easier:**
- Metadata joins stay in SQL
- Backup/restore with standard Postgres tooling
- Single Docker service covers both structured metadata and vectors

**Harder:**
- Approximate nearest neighbor (ANN) index tuning more limited than Qdrant/Weaviate
- Migration path if corpus grows beyond homelab would require re-indexing into purpose-built store

---

## Implementation Notes

- Docker Compose: `pgvector/pgvector:pg16`, port 5433 (5432 occupied by local Postgres)
- Schema: `chunks.embedding vector(768)`, IVFFlat index (`lists=100`, `vector_cosine_ops`)
- `dense_retrieve()` uses `ORDER BY c.embedding <=> %s::vector LIMIT k` — pgvector cosine distance operator
- `DB_CONFIG` read at call time (not import time) to avoid stale env var issue on module load

## Eval Impact

**Measured:** Phases 3–4, corpus of 3,332 chunks across 9 filings.

| Metric | Observed |
|--------|---------|
| Dense retrieval R@5 (pgvector) | 0.667 (dense-only baseline) |
| Dense retrieval R@5 (hybrid pipeline) | **1.000** |
| IVFFlat index build time | < 1s at 3,332 chunks |
| Dense query latency (incl. embedding call) | ~300–600ms per query |

**Verdict:** pgvector performs as expected at this corpus size. IVFFlat `lists=100` provides fast approximate nearest-neighbor search with no observable recall degradation. No performance issues encountered. Would evaluate Qdrant if corpus grows beyond ~100K chunks.
