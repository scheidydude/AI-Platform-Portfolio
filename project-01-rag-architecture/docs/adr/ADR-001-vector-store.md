# ADR-001: Vector Store Selection

**Status:** Draft
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

## Eval Impact

*(Populated in Phase 2 — before/after retrieval scores)*

| Metric | Score |
|--------|-------|
| Baseline retrieval recall@K | TBD |
| Post-tuning retrieval recall@K | TBD |
