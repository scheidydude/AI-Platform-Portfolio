"""
Phase 4 eval runner — LLM-as-judge across three retrieval configs.

Configs:
  hybrid_reranked   dense k=20 + BM25 k=20 + RRF + cross-encoder   (full pipeline)
  hybrid_no_rerank  dense k=20 + BM25 k=20 + RRF, no cross-encoder  (ablation ADR-004)
  dense_only        pgvector cosine top-5, no BM25 or re-ranker      (ablation ADR-003)

Run from project root:
    python src/eval/run_eval.py
"""
import os
import sys
import json
import time

_here = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_here, "..", ".."))
sys.path.insert(0, _project_root)

# Load .env before any DB/model imports
def _load_env(path):
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

from src.retrieval.search import (
    BM25Index, hybrid_search, hybrid_no_rerank, dense_top_n
)
from src.generation.generate import generate_answer
from src.eval.judge import judge_answer

GROUND_TRUTH_PATH = os.path.join(_project_root, "eval", "ground_truth.json")
RESULTS_PATH = os.path.join(_project_root, "eval", "results", "phase4_lm_judge_scores.json")


def recall_at_k(retrieved_ids: list, gt_ids: list, k: int) -> int:
    if not gt_ids:
        return 0
    return int(bool(set(gt_ids) & set(retrieved_ids[:k])))


def run() -> None:
    print("Loading ground truth...", flush=True)
    with open(GROUND_TRUTH_PATH) as f:
        gt = json.load(f)

    in_scope = [q for q in gt["questions"] if q["type"] != "out_of_scope"]
    print(f"In-scope questions: {len(in_scope)}", flush=True)

    print("Building BM25 index...", flush=True)
    bm25 = BM25Index()
    corpus_size = bm25.build()
    print(f"BM25 ready: {corpus_size} chunks", flush=True)

    configs = [
        ("hybrid_reranked",   "dense k=20 + BM25 k=20 + RRF k=60 + cross-encoder top5"),
        ("hybrid_no_rerank",  "dense k=20 + BM25 k=20 + RRF k=60 top5, no cross-encoder"),
        ("dense_only",        "pgvector cosine top-5, no BM25/RRF/re-ranker"),
    ]

    results = {
        "phase": 4,
        "date": "2026-05-23",
        "model": os.getenv("GEN_MODEL", "Qwen3.6-35B-A3B-MXFP4_MOE.gguf"),
        "configs": {name: desc for name, desc in configs},
        "per_question": {},
        "summary": {},
    }

    for q in in_scope:
        qid = q["id"]
        question = q["question"]
        gt_ids = q["ground_truth_chunk_ids"]
        results["per_question"][qid] = {"question": question, "type": q["type"], "configs": {}}
        print(f"\n{'='*60}\n{qid}: {question[:70]}", flush=True)

        for config_name, _ in configs:
            print(f"  [{config_name}] retrieving...", end=" ", flush=True)

            if config_name == "hybrid_reranked":
                chunks = hybrid_search(question, bm25, k_dense=20, k_sparse=20, top_n_rerank=5)
            elif config_name == "hybrid_no_rerank":
                chunks = hybrid_no_rerank(question, bm25, k_dense=20, k_sparse=20, top_n=5)
            else:
                chunks = dense_top_n(question, top_n=5)

            retrieved_ids = [c.chunk_id for c in chunks]
            r1 = recall_at_k(retrieved_ids, gt_ids, 1)
            r5 = recall_at_k(retrieved_ids, gt_ids, 5)

            print(f"R@1={r1} R@5={r5} | generating...", end=" ", flush=True)
            t0 = time.time()
            answer = generate_answer(question, chunks)
            gen_time = round(time.time() - t0, 1)

            print(f"({gen_time}s) | judging...", end=" ", flush=True)
            t0 = time.time()
            scores = judge_answer(question, chunks, answer)
            judge_time = round(time.time() - t0, 1)

            print(f"({judge_time}s) F={scores.faithfulness} C={scores.completeness} CA={scores.citation_accuracy} mean={scores.mean}", flush=True)

            results["per_question"][qid]["configs"][config_name] = {
                "retrieved_chunk_ids": retrieved_ids,
                "recall_at_1": r1,
                "recall_at_5": r5,
                "answer": answer,
                "scores": scores.to_dict(),
                "gen_time_s": gen_time,
                "judge_time_s": judge_time,
            }

    # Aggregate summary per config
    for config_name, config_desc in configs:
        q_data = [
            results["per_question"][q["id"]]["configs"][config_name]
            for q in in_scope
        ]
        n = len(q_data)
        results["summary"][config_name] = {
            "description": config_desc,
            "n_questions": n,
            "recall_at_1": round(sum(d["recall_at_1"] for d in q_data) / n, 3),
            "recall_at_5": round(sum(d["recall_at_5"] for d in q_data) / n, 3),
            "avg_faithfulness": round(sum(d["scores"]["faithfulness"] for d in q_data) / n, 3),
            "avg_completeness": round(sum(d["scores"]["completeness"] for d in q_data) / n, 3),
            "avg_citation_accuracy": round(sum(d["scores"]["citation_accuracy"] for d in q_data) / n, 3),
            "avg_mean_score": round(sum(d["scores"]["mean"] for d in q_data) / n, 3),
        }

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {RESULTS_PATH}", flush=True)

    # Print summary table
    print("\n=== SUMMARY ===")
    print(f"{'Config':<22} {'R@1':>5} {'R@5':>5} {'Faith':>6} {'Comp':>6} {'CiteA':>6} {'Mean':>6}")
    print("-" * 60)
    for config_name, _ in configs:
        s = results["summary"][config_name]
        print(f"{config_name:<22} {s['recall_at_1']:>5.3f} {s['recall_at_5']:>5.3f} "
              f"{s['avg_faithfulness']:>6.3f} {s['avg_completeness']:>6.3f} "
              f"{s['avg_citation_accuracy']:>6.3f} {s['avg_mean_score']:>6.3f}")


if __name__ == "__main__":
    run()
