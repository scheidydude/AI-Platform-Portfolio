CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    company TEXT,
    year INTEGER,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,                  -- e.g. "AAPL_2023_fixed_0042"
    document_id INTEGER REFERENCES documents(id),
    chunk_strategy TEXT NOT NULL,         -- "fixed", "semantic", "hierarchical"
    content TEXT NOT NULL,
    page_number INTEGER,
    section_title TEXT,
    parent_chunk_id TEXT,                 -- for hierarchical: sub-chunk's parent
    token_count INTEGER,
    embedding vector(768),                -- nomic-embed-text dim
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS chunks_strategy_idx ON chunks (chunk_strategy);
CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks (document_id);
