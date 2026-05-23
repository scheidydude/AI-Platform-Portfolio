"""
Phase 1 ingestion pipeline — orchestrates all steps:
  1. Download SEC 10-K PDFs from EDGAR
  2. Extract text/tables from PDFs
  3. Apply all 3 chunking strategies
  4. Embed and store to pgvector
  5. Print chunk samples for manual inspection

Usage:
  python -m src.ingestion.run_ingestion [--strategy fixed|semantic|hierarchical|all]
                                        [--embedding openai|local]
                                        [--skip-download]
                                        [--skip-embed]
                                        [--inspect N]
"""

import argparse
import json
from pathlib import Path

BASE = Path(__file__).parents[2]
RAW_DIR = BASE / "data" / "raw"
PROCESSED_DIR = BASE / "data" / "processed"
MANIFEST = RAW_DIR / "manifest.json"


def run_download():
    from .download_filings import main as download_main
    print("\n── Step 1: Downloading SEC 10-K filings ──")
    download_main()


def run_extraction():
    from .extract_pdf import batch_extract
    print("\n── Step 2: Extracting PDF text ──")
    paths = batch_extract(RAW_DIR, PROCESSED_DIR, MANIFEST)
    print(f"Extracted: {len(paths)} documents")
    return paths


def load_extracted_docs() -> list[dict]:
    docs = []
    for path in PROCESSED_DIR.glob("*_extracted.json"):
        with open(path) as f:
            docs.append(json.load(f))
    return docs


def run_chunking(docs: list[dict], strategies: list[str], embedding_backend: str) -> dict:
    from .chunkers import chunk_fixed, chunk_semantic, chunk_hierarchical, print_chunk_sample

    all_chunks = {}

    for doc in docs:
        print(f"\n  Document: {doc['company']} {doc['year']} ({doc['total_pages']} pages)")

        if "fixed" in strategies:
            chunks = chunk_fixed(doc)
            all_chunks.setdefault("fixed", []).extend(chunks)
            print(f"    fixed:        {len(chunks)} chunks")

        if "semantic" in strategies:
            chunks = chunk_semantic(doc)
            all_chunks.setdefault("semantic", []).extend(chunks)
            print(f"    semantic:     {len(chunks)} chunks")

        if "hierarchical" in strategies:
            chunks = chunk_hierarchical(doc)
            all_chunks.setdefault("hierarchical", []).extend(chunks)
            print(f"    hierarchical: {len(chunks)} chunks (includes parents)")

    return all_chunks


def run_embed_store(all_chunks: dict, embedding_backend: str):
    from .embed_and_store import store_chunks

    for strategy, chunks in all_chunks.items():
        print(f"\n  Storing {strategy} chunks ({len(chunks)} total)...")
        stored = store_chunks(chunks, backend=embedding_backend)
        print(f"  Stored: {stored} chunks embedded")


def inspect_chunks(all_chunks: dict, n: int = 5):
    from .chunkers import print_chunk_sample

    print("\n\n══════ CHUNK INSPECTION ══════")
    print("Manually review these samples. Ask: would this chunk answer a question in isolation?\n")
    for strategy, chunks in all_chunks.items():
        print_chunk_sample(chunks, n=n, label=strategy)


def main():
    parser = argparse.ArgumentParser(description="Phase 1: RAG ingestion pipeline")
    parser.add_argument("--strategy", default="all", choices=["fixed", "semantic", "hierarchical", "all"])
    parser.add_argument("--embedding", default="openai", choices=["openai", "local"])
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-embed", action="store_true")
    parser.add_argument("--inspect", type=int, default=5, help="Chunks to print per strategy")
    args = parser.parse_args()

    strategies = ["fixed", "semantic", "hierarchical"] if args.strategy == "all" else [args.strategy]

    if not args.skip_download:
        run_download()

    run_extraction()
    docs = load_extracted_docs()

    if not docs:
        print("No extracted documents found. Run without --skip-download first.")
        return

    print(f"\n── Step 3: Chunking {len(docs)} documents with strategies: {strategies} ──")
    all_chunks = run_chunking(docs, strategies, args.embedding)

    inspect_chunks(all_chunks, n=args.inspect)

    if not args.skip_embed:
        print(f"\n── Step 4: Embedding and storing to pgvector (backend={args.embedding}) ──")
        run_embed_store(all_chunks, args.embedding)
    else:
        print("\n[skip-embed] Skipping pgvector storage")

    print("\n── Phase 1 complete ──")
    print("Next: inspect chunks manually, then update ADR-002 with chunking decision")


if __name__ == "__main__":
    main()
