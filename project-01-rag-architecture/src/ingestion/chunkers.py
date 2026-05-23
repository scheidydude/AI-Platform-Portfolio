"""
Three chunking strategies for comparison:
  1. fixed   — fixed-size with overlap (512 tokens, 64 overlap)
  2. semantic — split on meaning shifts (LangChain SemanticChunker)
  3. hierarchical — section-level parent + sub-chunks

Each returns a list of Chunk objects with full metadata.
"""

import re
import numpy as np
import tiktoken
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional, List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

ChunkStrategy = Literal["fixed", "semantic", "hierarchical"]

TOKENIZER = tiktoken.get_encoding("cl100k_base")  # same as text-embedding-3-small


@dataclass
class Chunk:
    id: str
    document_filename: str
    company: str
    year: int
    strategy: ChunkStrategy
    content: str
    page_number: Optional[int]
    section_title: Optional[str]
    parent_chunk_id: Optional[str]  # hierarchical only
    token_count: int
    metadata: dict = field(default_factory=dict)


def token_count(text: str) -> int:
    return len(TOKENIZER.encode(text))


def make_id(company: str, year: int, strategy: str, index: int) -> str:
    safe = company.replace(" ", "_").upper()[:8]
    return f"{safe}_{year}_{strategy[:4].upper()}_{index:04d}"


# ─────────────────────────────────────────────
# Strategy 1: Fixed-size with overlap
# ─────────────────────────────────────────────

def chunk_fixed(doc: dict, chunk_size: int = 512, overlap: int = 64) -> List[Chunk]:
    """
    512-token chunks with 64-token overlap.
    Baseline strategy — simple, predictable, easy to reason about.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=token_count,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = []
    for page in doc["pages"]:
        if not page["text"].strip():
            continue
        splits = splitter.split_text(page["text"])
        for i, text in enumerate(splits):
            idx = len(chunks)
            chunks.append(
                Chunk(
                    id=make_id(doc["company"], doc["year"], "fixed", idx),
                    document_filename=doc["filename"],
                    company=doc["company"],
                    year=doc["year"],
                    strategy="fixed",
                    content=text,
                    page_number=page["page_number"],
                    section_title=page.get("section_hint"),
                    parent_chunk_id=None,
                    token_count=token_count(text),
                )
            )
    return chunks


# ─────────────────────────────────────────────
# Strategy 2: Semantic chunking
# ─────────────────────────────────────────────

_SEMANTIC_MODEL = None


def _get_semantic_model() -> SentenceTransformer:
    global _SEMANTIC_MODEL
    if _SEMANTIC_MODEL is None:
        _SEMANTIC_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _SEMANTIC_MODEL


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def chunk_semantic(
    doc: dict,
    min_chunk_tokens: int = 100,
    max_chunk_tokens: int = 800,
    breakpoint_percentile: float = 90,
) -> List[Chunk]:
    """
    Semantic chunking via sentence-level cosine similarity drops.
    Algorithm:
      1. Split text into sentences
      2. Embed each sentence with all-MiniLM-L6-v2
      3. Compute similarity between consecutive sentences
      4. Place chunk boundaries where similarity drops below percentile threshold
      5. Merge tiny chunks and split oversized ones
    """
    model = _get_semantic_model()

    full_text = doc["raw_text"]
    if not full_text.strip():
        return []

    # Split into sentences (rough but fast)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", full_text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]

    if len(sentences) < 3:
        # Document too short for semantic splitting — fall back to fixed
        return chunk_fixed(doc)

    # Embed all sentences
    embeddings = model.encode(sentences, show_progress_bar=False, batch_size=64)

    # Compute consecutive similarity
    sims = [_cosine_sim(embeddings[i], embeddings[i + 1]) for i in range(len(embeddings) - 1)]

    # Breakpoint: where similarity drops below threshold
    threshold = float(np.percentile(sims, 100 - breakpoint_percentile))
    boundaries = {0}
    for i, sim in enumerate(sims):
        if sim < threshold:
            boundaries.add(i + 1)
    boundaries.add(len(sentences))
    boundaries = sorted(boundaries)

    # Build raw segment texts
    segments = []
    for i in range(len(boundaries) - 1):
        seg_sentences = sentences[boundaries[i] : boundaries[i + 1]]
        segments.append(" ".join(seg_sentences))

    # Merge tiny segments and split huge ones
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_tokens,
        chunk_overlap=32,
        length_function=token_count,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    buffer = ""
    for seg in segments:
        candidate = (buffer + " " + seg).strip() if buffer else seg
        if token_count(candidate) < min_chunk_tokens:
            buffer = candidate
        elif token_count(candidate) > max_chunk_tokens:
            # Flush buffer first
            if buffer:
                for part in splitter.split_text(buffer):
                    idx = len(chunks)
                    chunks.append(Chunk(
                        id=make_id(doc["company"], doc["year"], "semantic", idx),
                        document_filename=doc["filename"],
                        company=doc["company"],
                        year=doc["year"],
                        strategy="semantic",
                        content=part,
                        page_number=None,
                        section_title=None,
                        parent_chunk_id=None,
                        token_count=token_count(part),
                    ))
                buffer = ""
            for part in splitter.split_text(seg):
                idx = len(chunks)
                chunks.append(Chunk(
                    id=make_id(doc["company"], doc["year"], "semantic", idx),
                    document_filename=doc["filename"],
                    company=doc["company"],
                    year=doc["year"],
                    strategy="semantic",
                    content=part,
                    page_number=None,
                    section_title=None,
                    parent_chunk_id=None,
                    token_count=token_count(part),
                ))
        else:
            if buffer:
                idx = len(chunks)
                chunks.append(Chunk(
                    id=make_id(doc["company"], doc["year"], "semantic", idx),
                    document_filename=doc["filename"],
                    company=doc["company"],
                    year=doc["year"],
                    strategy="semantic",
                    content=buffer,
                    page_number=None,
                    section_title=None,
                    parent_chunk_id=None,
                    token_count=token_count(buffer),
                ))
            buffer = seg

    if buffer:
        idx = len(chunks)
        chunks.append(Chunk(
            id=make_id(doc["company"], doc["year"], "semantic", idx),
            document_filename=doc["filename"],
            company=doc["company"],
            year=doc["year"],
            strategy="semantic",
            content=buffer,
            page_number=None,
            section_title=None,
            parent_chunk_id=None,
            token_count=token_count(buffer),
        ))

    return chunks


# ─────────────────────────────────────────────
# Strategy 3: Hierarchical chunking
# ─────────────────────────────────────────────

ITEM_HEADER = re.compile(
    r"(?im)^(Item\s+\d+[A-Za-z]?\.\s+[A-Za-z][^\n]{2,80})\s*$",
)


def split_into_sections(raw_text: str) -> list[tuple[str, str]]:
    """Split document into (section_title, section_text) pairs."""
    matches = list(ITEM_HEADER.finditer(raw_text))
    if not matches:
        return [("DOCUMENT", raw_text)]

    # Collect all candidate sections (title, text)
    candidates = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        section_text = raw_text[start:end].strip()
        candidates.append((title, section_text))

    # Deduplicate: for each item number, keep the instance with most content.
    # TOC entries and real sections both match — the real section has far more text.
    item_num_re = re.compile(r"Item\s+(\d+[A-Za-z]?)", re.IGNORECASE)
    best: dict = {}
    for title, text in candidates:
        m = item_num_re.search(title)
        key = m.group(1).lower() if m else title
        if key not in best or len(text) > len(best[key][1]):
            best[key] = (title, text)

    # Return in item-number order, include all items (even short ones like "None")
    def item_sort_key(k: str):
        nums = re.findall(r"\d+", k)
        letters = re.findall(r"[a-z]", k)
        return (int(nums[0]) if nums else 0, letters[0] if letters else "")

    sections = [best[k] for k in sorted(best, key=item_sort_key)]
    return sections


def chunk_hierarchical(
    doc: dict,
    sub_chunk_size: int = 512,
    sub_chunk_overlap: int = 64,
) -> List[Chunk]:
    """
    Hierarchical: store full sections (parent) + sub-chunks (children).
    Retrieval uses sub-chunks; LLM context receives the parent section.
    Best for dense regulatory text — preserves context around retrieved passages.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=sub_chunk_size,
        chunk_overlap=sub_chunk_overlap,
        length_function=token_count,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = []
    sections = split_into_sections(doc["raw_text"])
    parent_idx = 0

    for section_title, section_text in sections:
        if not section_text.strip():
            continue

        # Parent chunk — full section, not embedded separately
        parent_id = make_id(doc["company"], doc["year"], "hier_parent", parent_idx)
        parent_chunk = Chunk(
            id=parent_id,
            document_filename=doc["filename"],
            company=doc["company"],
            year=doc["year"],
            strategy="hierarchical",
            content=section_text,
            page_number=None,
            section_title=section_title,
            parent_chunk_id=None,
            token_count=token_count(section_text),
            metadata={"is_parent": True},
        )
        chunks.append(parent_chunk)
        parent_idx += 1

        # Sub-chunks — these get embedded and indexed for retrieval
        sub_splits = splitter.split_text(section_text)
        for j, sub_text in enumerate(sub_splits):
            sub_id = make_id(doc["company"], doc["year"], "hier_sub", len(chunks))
            chunks.append(
                Chunk(
                    id=sub_id,
                    document_filename=doc["filename"],
                    company=doc["company"],
                    year=doc["year"],
                    strategy="hierarchical",
                    content=sub_text,
                    page_number=None,
                    section_title=section_title,
                    parent_chunk_id=parent_id,
                    token_count=token_count(sub_text),
                    metadata={"is_parent": False, "sub_index": j},
                )
            )

    return chunks


# ─────────────────────────────────────────────
# Utility: inspect chunks for manual review
# ─────────────────────────────────────────────

def print_chunk_sample(chunks: List[Chunk], n: int = 5, label: str = ""):
    print(f"\n{'='*60}")
    print(f"Strategy: {label or chunks[0].strategy if chunks else 'unknown'}")
    print(f"Total chunks: {len(chunks)}")
    if chunks:
        sizes = [c.token_count for c in chunks]
        print(f"Token count — min:{min(sizes)} max:{max(sizes)} avg:{sum(sizes)//len(sizes)}")
    print(f"{'='*60}")
    for chunk in chunks[:n]:
        print(f"\n[{chunk.id}] section={chunk.section_title} tokens={chunk.token_count}")
        if chunk.parent_chunk_id:
            print(f"  parent={chunk.parent_chunk_id}")
        print(f"  {chunk.content[:300].strip()}...")
