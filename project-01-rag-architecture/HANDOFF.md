# HANDOFF — RAG Architecture POC
**Written:** 2026-05-23  
**Phase completed:** Phase 1 (Corpus & Ingestion)  
**Phase starting:** Phase 2 (Retrieval)

---

## 1. Mission

Build a production-quality RAG pipeline over SEC 10-K filings, with heavy emphasis on retrieval quality (not just ingestion). This is a career artifact project — every significant decision must be documented in ADRs, design docs, and kept current in `INDEX.md`. The deliverable is both a functional POC and a documentation portfolio suitable for an AI Architect interview.

---

## 2. Current State

### Working and verified
- **pgvector DB running:** Docker container `rag_postgres` on port **5433** (not 5432 — see Gotchas). Schema: `documents` + `chunks` tables with `vector(768)`.
- **3,344 chunks in DB:** 3,332 have embeddings (768-dim nomic-embed-text). 12 are parent stubs (stored without embeddings, used as context holders).
- **Dense retrieval works end-to-end:** Embedding a query against `http://ai.scheidy.com:8081/v1` and running `ORDER BY c.embedding <=> %s::vector LIMIT K` returns semantically correct results. Verified manually with the query "What are the main liquidity risks for JPMorgan Chase?" — top results correctly pull from JPMorgan Item 1A Risk Factors.
- **9 documents ingested:** Apple, Microsoft, JPMorgan Chase, Goldman Sachs, Bank of America, Citigroup, Wells Fargo, Morgan Stanley, BlackRock. All in `data/raw/*.htm` and `data/processed/*_extracted.json`.
- **Chunking strategy: hierarchical.** Decision documented in `docs/design/chunking-decision.md` and `docs/adr/ADR-002-chunking-strategy.md` (status: Decided).
- **ADR-002 and ADR-005 decided.** ADR-001, ADR-003, ADR-004 are drafted but need eval impact data (filled in Phase 3-4).

### Known gaps (not blockers for Phase 2)
- **Citigroup and Morgan Stanley:** Section detection fell back to single "DOCUMENT" parent — their HTML uses `1.` not `Item 1.` format. All sub-chunks still embedded and searchable; they just lack `section_title` granularity. ~1,063 combined embedded chunks are in the DB and retrieval-ready.
- **Wells Fargo:** Only 24 embedded chunks. The downloaded file (`wfc-20251231_d2.htm`) was a TOC/index wrapper, not the full 10-K body. Does not materially affect corpus coverage given the other 8 dense filings.
- **`run_ingestion.py` is stale:** It still references `--embedding openai|local` flags and `batch_extract` filtering for `.pdf` suffix. Do not use it — run chunking and embedding directly as shown below.
- **Charles Schwab:** Not downloaded. EDGAR submissions JSON returned no 10-K form type for their CIK `0000316888`. Skip for now — 9 filings is sufficient corpus.
- **`src/retrieval/`, `src/generation/`, `src/eval/`:** Directories exist, all empty. No `__init__.py` at `src/` level.

### Exact next action
Build `src/retrieval/search.py` implementing hybrid search: dense (pgvector cosine) + sparse (BM25 via rank_bm25) fused with RRF, then add cross-encoder re-ranking. See Phase 2 plan in `task_plan.md`.

---

## 3. Decisions Made (and Why)

**Decision:** Hierarchical chunking strategy  
**Alternatives:** Fixed-size (512t/64 overlap), semantic (cosine similarity drops)  
**Reason:** SEC 10-K Item boundaries (Item 1A Risk Factors, Item 7 MD&A) are semantically correct chunk boundaries. Sub-chunks (retrieval targets) inherit section context via `parent_chunk_id`; full parent section passed to LLM for generation. Fixed-size cuts mid-disclosure; semantic produces 3–6 token orphan chunks from financial tables.  
**Reversibility:** Load-bearing — changing strategy means re-chunking and re-embedding all 9 docs. Possible but slow (~20 min ingestion).

---

**Decision:** nomic-embed-text local server for embeddings  
**Alternatives:** OpenAI `text-embedding-3-small` (1536 dims, API)  
**Reason:** Homelab inference server already running at `http://ai.scheidy.com:8081/v1`. Zero extra cost/setup. OpenAI-compatible API — switching later is one env var change.  
**Reversibility:** Easy to swap model, but requires full re-ingestion + schema drop/recreate (dimension change: 768 → 1536). DB schema currently fixed at `vector(768)`.

---

**Decision:** pgvector on Docker port 5433  
**Alternatives:** Port 5432 (default)  
**Reason:** Local Postgres installation already owns port 5432 on this machine. Docker was shadowed; connections hit local Postgres (no `rag_user` role there).  
**Reversibility:** Trivial — just an env var. `.env` has `PGPORT=5433`.

---

**Decision:** EDGAR HTML filings (.htm) instead of PDFs  
**Alternatives:** PDF download (pdfplumber)  
**Reason:** EDGAR's `submissions.json` API provides `primaryDocument` field which points to `.htm` files. These are the complete inline XBRL HTML filings — full text, no PDF parsing needed.  
**Reversibility:** Irrelevant — PDFs aren't readily available from EDGAR's JSON API anyway.

---

**Decision:** Custom HTML extractor (not BeautifulSoup)  
**Alternatives:** BeautifulSoup, pdfplumber  
**Reason:** EDGAR `.htm` files embed inline XBRL (iXBRL) data — garbled namespace strings like `http://fasb.org/us-gaap/2025#LongTermDebtNoncurrent`. Built a custom `HTMLParser` subclass with `_is_xbrl_noise()` filter that skips these. BeautifulSoup would also work but wasn't installed.  
**Reversibility:** Easy to swap.

---

**Decision:** Implement SemanticChunker from scratch instead of langchain-experimental  
**Alternatives:** `langchain_experimental.text_splitter.SemanticChunker`  
**Reason:** `langchain-experimental` failed to install due to broken `packaging` metadata in the conda env. Built equivalent using sentence-transformers cosine similarity. Result: more transparent and auditable for the career artifact.  
**Reversibility:** Could revisit if env is fixed, but current implementation is fine.

---

## 4. Architecture & Key Files

```
project-01-rag-architecture/
├── .env                          # All config — load manually (see Gotchas)
├── docker-compose.yml            # pgvector/pgvector:pg16, port 5433:5432
├── scripts/init_db.sql           # Schema: documents + chunks (vector(768))
├── requirements.txt              # pip deps — python-dotenv NOT included yet
│
├── src/ingestion/
│   ├── download_filings.py       # EDGAR submissions JSON API downloader
│   ├── extract_pdf.py            # HTML/PDF extractor; custom XBRL noise filter
│   ├── chunkers.py               # 3 strategies: chunk_fixed, chunk_semantic,
│   │                             #   chunk_hierarchical. Use chunk_hierarchical.
│   ├── embed_and_store.py        # Calls nomic-embed-text; stores to pgvector
│   └── run_ingestion.py          # STALE — do not use (see Current State)
│
├── src/retrieval/                # EMPTY — Phase 2 work goes here
├── src/generation/               # EMPTY — Phase 3 work goes here
├── src/eval/                     # EMPTY — Phase 4 work goes here
│
├── data/raw/*.htm                # 9 EDGAR 10-K filings (HTML format)
├── data/raw/manifest.json        # company → path mapping
├── data/processed/*_extracted.json  # Extracted text, ~200KB–1.4MB each
│
├── docs/
│   ├── SRS.md                    # Requirements spec — keep updated
│   ├── adr/ADR-001-vector-store.md      # Decided: pgvector
│   ├── adr/ADR-002-chunking-strategy.md # Decided: hierarchical
│   ├── adr/ADR-003-hybrid-search.md     # Drafted, needs eval impact
│   ├── adr/ADR-004-reranker.md          # Drafted, needs eval impact
│   ├── adr/ADR-005-embedding-model.md   # Decided: nomic-embed-text local
│   └── design/chunking-decision.md      # Complete — Phase 1 deliverable
│
├── INDEX.md                      # Running artifact index — update every session
├── task_plan.md                  # Phase tracker + decisions log
├── findings.md                   # Research notes
└── progress.md                   # Session log + score history
```

**Do not touch** `data/raw/*.htm` and `data/processed/*.json` — regenerating these costs ~15 min of EDGAR downloads + re-extraction.

---

## 5. Gotchas & Hard-Won Knowledge

**Port 5432 is local Postgres, not Docker.** Docker pgvector listens on 5433. Every DB connection must use port 5433. `.env` has this set. If you get `role "rag_user" does not exist`, you're hitting local Postgres.

**Python 3.9.7 (miniforge conda).** `X | None` and `list[str]` type hints crash at runtime. Always use `Optional[X]` and `List[str]` from `typing`. Any new code using 3.10+ union syntax will fail on import.

**Load `.env` manually — no python-dotenv installed.** Pattern used throughout:
```python
for line in open('.env'):
    line = line.strip()
    if line and '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ.setdefault(k, v)
```
Consider adding `python-dotenv` to `requirements.txt` and using `load_dotenv()` going forward.

**`DB_CONFIG` in `embed_and_store.py` is computed at import time.** If you set env vars after importing the module, the dict already has stale values. Set env before importing, or refactor to read env at call time.

**XBRL noise in EDGAR HTML.** The first ~15% of most `.htm` files is inline XBRL structured data (namespace URLs, long identifiers). Without the `_is_xbrl_noise()` filter in `extract_pdf.py`, early chunks are garbage. Do not remove or relax this filter.

**Citigroup and Morgan Stanley section detection fails.** These filings use `1.` / `1A.` section labels without the word "Item". `split_into_sections()` regex `^(Item\s+\d+[A-Za-z]?\.\s+...)$` misses them — fallback is single "DOCUMENT" parent covering the entire doc. Their sub-chunks are still in the DB and retrieval-ready; they just lack `section_title` granularity.

**ITEM headers in EDGAR are two formats.** TOC entries: `Item 1.\nBusiness.` (two lines). Content body: `Item 1. Business.` (single line). The regex matches the single-line content format. Do not change the regex to match two-line format — that captured TOC entries with 1–7 token content.

**`sentence-transformers` import needs working `packaging` metadata.** If you get `ValueError: Unable to compare versions for packaging>=20.0`, run: `pip3 install --ignore-installed packaging`. Fixed in current env.

**Wells Fargo file is a TOC wrapper.** `data/raw/Wells_Fargo_2026_10K.htm` is 86KB (30 pages) vs 8–15MB for real filings. The `primaryDocument` from their submission pointed to an index page. If a full WF 10-K is needed, manually download from EDGAR and re-run extraction + embedding for that file.

---

## 6. Conventions In Play

- **ADRs are required for all major decisions** — see spec. Format: Context / Options / Decision / Rationale / Consequences / Eval Impact. Fill eval impact sections after Phase 3 scoring.
- **INDEX.md is the rollup** — update status column every session when artifacts change state.
- **task_plan.md tracks phases** — update status `not_started` → `in_progress` → `complete`.
- **Caveman communication mode** is active (set by hook). Claude responses are terse. Not relevant to code.
- **No unit tests.** POC phase — we test by running the actual pipeline and inspecting outputs.
- **Type hints:** Use `typing` module (`Optional`, `List`, `Dict`, `Tuple`) not 3.10+ syntax.
- **Env config:** Everything in `.env`. DB defaults match `.env` values (no hardcoded passwords in code except defaults that match `.env`).
- **No git history** — this repo has no commits yet. No `.gitignore` either — add one before first commit (exclude `data/raw/`, `data/processed/`, `__pycache__/`, `.env`).

---

## 7. Open Questions

1. **LLM for generation (Phase 2/3):** Spec says Claude API or local Qwen, swap and compare. Is `ANTHROPIC_API_KEY` available in this environment? If not, start with local Qwen on the homelab server. Decide before building `src/generation/`.

2. **LLM-as-judge (Phase 4):** Same question — Claude API judge vs. local model judge. Need API key or local model URL.

3. **Should Wells Fargo be replaced?** 24 chunks from a TOC wrapper is noise. Options: (a) ignore it, (b) manually download the full WF 10-K and re-ingest. Does not affect Phase 2 functionality.

4. **Citigroup/Morgan Stanley section granularity:** Their chunks have `section_title = "DOCUMENT"` instead of Item-level labels. For Phase 3 eval set, avoid writing ground truth questions that rely on section filtering for these two companies. Or fix the section regex first — worth doing if eval set quality matters.

5. **`python-dotenv` in requirements?** Would clean up the manual env-loading boilerplate in every script. Low friction to add.

---

## 8. Do Not Touch

- `data/raw/*.htm` — do not delete or re-download without good reason (EDGAR rate limits).
- `data/processed/*.json` — expensive to regenerate; re-extract only if `extract_pdf.py` logic changes.
- `scripts/init_db.sql` — schema is `vector(768)`. Do not change dimensions without dropping and recreating the `chunks` table and re-embedding everything.
- `docs/design/chunking-decision.md` — Phase 1 deliverable, complete. Do not reopen the chunking strategy debate unless user asks.
- `docs/adr/ADR-002` and `ADR-005` — both marked Decided. Do not change status or reopen decisions.
- The `ITEM_HEADER` regex in `chunkers.py` — matches single-line `Item 1. Business.` format. Do not change to two-line format (that re-introduces TOC capture bug).

---

## 9. Resume Command

> Read `HANDOFF.md` and `task_plan.md`. Phase 1 is complete. Begin Phase 2: build `src/retrieval/search.py` implementing hybrid search — dense pgvector cosine + BM25 sparse (rank_bm25) + RRF fusion + cross-encoder re-ranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`). Then build `src/retrieval/api.py` as a simple retrieval endpoint. After retrieval is working, write `docs/design/retrieval-design.md` and update ADR-003 and ADR-004. Load `.env` before any DB or embedding calls (see Gotchas — no python-dotenv). Do not change chunking strategy or re-embed the corpus. Confirm before writing anything outside `src/retrieval/` and `docs/`.
