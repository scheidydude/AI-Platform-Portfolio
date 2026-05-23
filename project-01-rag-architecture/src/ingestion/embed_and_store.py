"""
Embed chunks and store in pgvector.
Embedding backend: local nomic-embed-text via OpenAI-compatible API at ai.scheidy.com:8081
"""

import os
import json
import time
import psycopg2
import psycopg2.extras
from pathlib import Path
from typing import List, Dict

from .chunkers import Chunk

EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://ai.scheidy.com:8081/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", 768))

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", 5432)),
    "dbname": os.getenv("PGDATABASE", "rag_db"),
    "user": os.getenv("PGUSER", "rag_user"),
    "password": os.getenv("PGPASSWORD", "rag_pass"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_embedder():
    """
    OpenAI-compatible embedder pointing at local nomic-embed-text server.
    Server: http://ai.scheidy.com:8081/v1
    Model: nomic-embed-text (768 dims)
    """
    from openai import OpenAI
    client = OpenAI(base_url=EMBED_BASE_URL, api_key="not-needed")

    def embed(texts: List[str]) -> List[List[float]]:
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [item.embedding for item in resp.data]

    return embed


def upsert_document(conn, filename: str, company: str, year: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (filename, company, year)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (filename, company, year),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("SELECT id FROM documents WHERE filename = %s", (filename,))
        return cur.fetchone()[0]


def store_chunks(
    chunks: List[Chunk],
    batch_size: int = 50,
    skip_parents: bool = True,
) -> int:
    """
    Embed and store chunks in pgvector.
    skip_parents=True: hierarchical parent chunks stored for context but not embedded
    """
    embed = get_embedder()
    conn = get_connection()
    stored = 0

    try:
        by_doc: Dict[str, List[Chunk]] = {}
        for chunk in chunks:
            by_doc.setdefault(chunk.document_filename, []).append(chunk)

        for filename, doc_chunks in by_doc.items():
            first = doc_chunks[0]
            doc_id = upsert_document(conn, filename, first.company, first.year)

            to_embed = [c for c in doc_chunks if not (skip_parents and c.metadata.get("is_parent"))]
            to_store_only = [c for c in doc_chunks if skip_parents and c.metadata.get("is_parent")]

            for i in range(0, len(to_embed), batch_size):
                batch = to_embed[i : i + batch_size]
                embeddings = embed([c.content for c in batch])

                with conn.cursor() as cur:
                    for chunk, embedding in zip(batch, embeddings):
                        cur.execute(
                            """
                            INSERT INTO chunks
                              (id, document_id, chunk_strategy, content,
                               page_number, section_title, parent_chunk_id,
                               token_count, embedding, metadata)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,%s)
                            ON CONFLICT (id) DO UPDATE SET
                              content = EXCLUDED.content,
                              embedding = EXCLUDED.embedding
                            """,
                            (
                                chunk.id, doc_id, chunk.strategy, chunk.content,
                                chunk.page_number, chunk.section_title,
                                chunk.parent_chunk_id, chunk.token_count,
                                str(embedding), json.dumps(chunk.metadata),
                            ),
                        )
                        stored += 1
                conn.commit()
                print(f"    embedded {min(i+batch_size, len(to_embed))}/{len(to_embed)} chunks", end="\r")

            for chunk in to_store_only:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chunks
                          (id, document_id, chunk_strategy, content,
                           page_number, section_title, parent_chunk_id,
                           token_count, metadata)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            chunk.id, doc_id, chunk.strategy, chunk.content,
                            chunk.page_number, chunk.section_title,
                            chunk.parent_chunk_id, chunk.token_count,
                            json.dumps(chunk.metadata),
                        ),
                    )
                conn.commit()

    finally:
        conn.close()

    return stored
