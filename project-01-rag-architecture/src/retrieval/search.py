"""
Hybrid retrieval: dense pgvector cosine + BM25 sparse, fused via RRF,
then cross-encoder re-ranked.

Run from project root. Load .env before importing (python-dotenv not installed).
"""
import os
import re
from typing import List, Dict, Optional

import psycopg2
import psycopg2.extras
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder


def load_env(path: str = ".env") -> None:
    """Manual .env loader — python-dotenv not installed in this env."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


def _db_config() -> Dict:
    # Read at call time, not import time — avoids stale values if env set after import.
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", 5433)),
        "dbname": os.getenv("PGDATABASE", "rag_db"),
        "user": os.getenv("PGUSER", "rag_user"),
        "password": os.getenv("PGPASSWORD", "rag_pass"),
    }


def _get_conn():
    return psycopg2.connect(**_db_config())


def _embed_query(query: str) -> List[float]:
    from openai import OpenAI
    client = OpenAI(
        base_url=os.getenv("EMBED_BASE_URL", "http://ai.scheidy.com:8081/v1"),
        api_key="not-needed",
    )
    resp = client.embeddings.create(
        model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
        input=[query],
    )
    return resp.data[0].embedding


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())


class ChunkResult:
    def __init__(
        self,
        chunk_id: str,
        content: str,
        section_title: Optional[str],
        company: Optional[str],
        year: Optional[int],
        score: float = 0.0,
        parent_chunk_id: Optional[str] = None,
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.section_title = section_title
        self.company = company
        self.year = year
        self.score = score
        self.parent_chunk_id = parent_chunk_id

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "section_title": self.section_title,
            "company": self.company,
            "year": self.year,
            "score": self.score,
            "parent_chunk_id": self.parent_chunk_id,
        }


def dense_retrieve(query: str, k: int = 20) -> List[ChunkResult]:
    """Top-k chunks by pgvector cosine similarity."""
    embedding = _embed_query(query)
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT c.id, c.content, c.section_title, c.parent_chunk_id,
                       d.company, d.year,
                       1 - (c.embedding <=> %s::vector) AS cosine_sim
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (str(embedding), str(embedding), k),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        ChunkResult(
            chunk_id=row["id"],
            content=row["content"],
            section_title=row["section_title"],
            company=row["company"],
            year=row["year"],
            score=float(row["cosine_sim"]),
            parent_chunk_id=row["parent_chunk_id"],
        )
        for row in rows
    ]


def _fetch_all_chunks_for_bm25() -> List[Dict]:
    """Fetch all embedded chunks for BM25 corpus construction."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT c.id, c.content, c.section_title, c.parent_chunk_id,
                       d.company, d.year
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.id
                """
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


class BM25Index:
    """BM25Okapi index over all embedded corpus chunks. Build once at startup."""

    def __init__(self) -> None:
        self._chunks: List[Dict] = []
        self._bm25: Optional[BM25Okapi] = None

    def build(self) -> int:
        """Fetch corpus from DB and build index. Returns corpus size."""
        self._chunks = _fetch_all_chunks_for_bm25()
        tokenized = [_tokenize(c["content"]) for c in self._chunks]
        self._bm25 = BM25Okapi(tokenized)
        return len(self._chunks)

    def retrieve(self, query: str, k: int = 20) -> List[ChunkResult]:
        if self._bm25 is None:
            raise RuntimeError("BM25Index not built — call build() first")
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [
            ChunkResult(
                chunk_id=self._chunks[i]["id"],
                content=self._chunks[i]["content"],
                section_title=self._chunks[i]["section_title"],
                company=self._chunks[i]["company"],
                year=self._chunks[i]["year"],
                score=float(scores[i]),
                parent_chunk_id=self._chunks[i]["parent_chunk_id"],
            )
            for i in top_idx
        ]


def rrf_fuse(
    dense: List[ChunkResult],
    sparse: List[ChunkResult],
    k: int = 60,
    top_n: int = 20,
) -> List[ChunkResult]:
    """
    Reciprocal Rank Fusion (Cormack et al., 2009).
    RRF(d) = sum(1 / (k + rank(d))) across ranked lists.
    k=60 is the standard constant — no tuning required.
    """
    rrf_scores: Dict[str, float] = {}
    index: Dict[str, ChunkResult] = {}

    for rank, r in enumerate(dense, start=1):
        rrf_scores[r.chunk_id] = rrf_scores.get(r.chunk_id, 0.0) + 1.0 / (k + rank)
        index[r.chunk_id] = r

    for rank, r in enumerate(sparse, start=1):
        rrf_scores[r.chunk_id] = rrf_scores.get(r.chunk_id, 0.0) + 1.0 / (k + rank)
        if r.chunk_id not in index:
            index[r.chunk_id] = r

    ranked_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_n]
    fused = []
    for cid in ranked_ids:
        r = index[cid]
        r.score = rrf_scores[cid]
        fused.append(r)
    return fused


_cross_encoder_instance: Optional[CrossEncoder] = None


def _get_cross_encoder() -> CrossEncoder:
    global _cross_encoder_instance
    if _cross_encoder_instance is None:
        _cross_encoder_instance = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder_instance


def rerank(query: str, chunks: List[ChunkResult], top_n: int = 5) -> List[ChunkResult]:
    """Cross-encoder re-rank. Jointly scores (query, chunk) pairs."""
    if not chunks:
        return chunks
    ce = _get_cross_encoder()
    pairs = [[query, c.content] for c in chunks]
    scores = ce.predict(pairs)
    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)[:top_n]
    result = []
    for score, chunk in ranked:
        chunk.score = float(score)
        result.append(chunk)
    return result


def hybrid_search(
    query: str,
    bm25_index: BM25Index,
    k_dense: int = 20,
    k_sparse: int = 20,
    rrf_k: int = 60,
    top_n_fused: int = 20,
    top_n_rerank: int = 5,
) -> List[ChunkResult]:
    """
    Full retrieval pipeline:
      1. Dense retrieval — pgvector cosine, top k_dense
      2. Sparse retrieval — BM25, top k_sparse
      3. RRF fusion — top top_n_fused candidates
      4. Cross-encoder re-rank — top top_n_rerank returned

    Returns top_n_rerank ChunkResult objects with cross-encoder scores.
    """
    dense = dense_retrieve(query, k=k_dense)
    sparse = bm25_index.retrieve(query, k=k_sparse)
    fused = rrf_fuse(dense, sparse, k=rrf_k, top_n=top_n_fused)
    return rerank(query, fused, top_n=top_n_rerank)
