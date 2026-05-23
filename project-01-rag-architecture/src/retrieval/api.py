"""
Retrieval API — Flask wrapper over hybrid_search.

Start from project root:
    python src/retrieval/api.py

Endpoints:
    GET  /health       — liveness + BM25 readiness
    POST /search       — hybrid search with re-ranking
    POST /search/dense — dense-only (pgvector), no BM25 or re-ranker
"""
import os
import sys

# Resolve project root so this runs correctly from any working directory.
_here = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_here, "..", ".."))
sys.path.insert(0, _project_root)
sys.path.insert(0, _here)  # for direct `python api.py` invocation

# Load .env before any module that reads DB/embed env vars.
def _load_env(path: str) -> None:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass

_load_env(os.path.join(_project_root, ".env"))

from flask import Flask, request, jsonify
from src.retrieval.search import BM25Index, hybrid_search, dense_retrieve, rerank

app = Flask(__name__)

_bm25_index = BM25Index()
_bm25_ready = False


def _ensure_bm25() -> None:
    global _bm25_ready
    if not _bm25_ready:
        count = _bm25_index.build()
        print(f"[startup] BM25 index built: {count} chunks", flush=True)
        _bm25_ready = True


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bm25_ready": _bm25_ready})


@app.route("/search", methods=["POST"])
def search():
    """
    Hybrid search: dense + BM25 + RRF + cross-encoder re-rank.

    Request body (JSON):
        query     string  required
        top_n     int     default 5   — final results returned (after re-rank)
        k_dense   int     default 20  — candidates from dense retrieval
        k_sparse  int     default 20  — candidates from BM25 retrieval

    Response:
        { query, top_n, results: [ { chunk_id, content, section_title,
                                     company, year, score, parent_chunk_id } ] }
    """
    _ensure_bm25()
    body = request.get_json(force=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    top_n = int(body.get("top_n", 5))
    k_dense = int(body.get("k_dense", 20))
    k_sparse = int(body.get("k_sparse", 20))

    results = hybrid_search(
        query=query,
        bm25_index=_bm25_index,
        k_dense=k_dense,
        k_sparse=k_sparse,
        top_n_rerank=top_n,
    )
    return jsonify({
        "query": query,
        "top_n": top_n,
        "results": [r.to_dict() for r in results],
    })


@app.route("/search/dense", methods=["POST"])
def search_dense():
    """
    Dense-only retrieval (pgvector cosine, no BM25 or re-ranker).
    Useful for ablation: compare dense-only vs hybrid recall.

    Request body (JSON):
        query   string  required
        top_n   int     default 5
    """
    body = request.get_json(force=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    top_n = int(body.get("top_n", 5))
    results = dense_retrieve(query, k=top_n)
    return jsonify({
        "query": query,
        "top_n": top_n,
        "results": [r.to_dict() for r in results],
    })


if __name__ == "__main__":
    _ensure_bm25()
    port = int(os.getenv("RETRIEVAL_PORT", 8080))
    print(f"[api] listening on 0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)
