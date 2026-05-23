# Project Retrospective — RAG Architecture POC

**Author:** David Scheiderman
**Project:** Project 01 — RAG Architecture over SEC 10-K Filings
**Duration:** 4 days (2026-05-22 to 2026-05-23, accelerated)
**Status:** Complete

---

## What Was Built

A production-quality RAG pipeline over 9 SEC 10-K filings (Apple, Microsoft, JPMorgan Chase, Goldman Sachs, Bank of America, Citigroup, Wells Fargo, Morgan Stanley, BlackRock). The pipeline covers ingestion → chunking → embedding → hybrid retrieval → generation → automated evaluation, with full ADR documentation.

Final eval results: R@1=0.933, R@5=1.000, avg faithfulness=5.000/5, avg mean score=4.600/5 across 15 in-scope questions.

---

## What Went Well

**Hierarchical chunking decision was correct.** The choice to use 10-K Item boundaries as chunk boundaries paid off immediately — `section_title` metadata on every chunk gave retrieval results that are auditable ("Item 1A. Risk Factors." is a meaningful citation, not "chunk 42"). The parent_chunk_id path for future full-section context passing is clean.

**pgvector was zero-friction.** Adding the pgvector extension to a Postgres container cost nothing operationally. The IVFFlat index performed well on 3,332 chunks with no tuning needed. The SQL join (`chunks JOIN documents`) for metadata retrieval was cleaner than any purpose-built vector DB client would have been.

**BM25 exact-match wins were measurable.** The Phase 4 ablation confirmed the ADR-003 hypothesis: dense-only R@1=0.533 vs hybrid R@1=0.933. The wins were exactly where predicted — Goldman Sachs market risk (precise terminology), multi-source stress testing queries (exact term "stress testing" vs semantic embedding). The ADR rationale written before building turned out to be empirically correct.

**Cross-encoder R@1 improvement was larger than expected.** ADR-004 predicted "significant quality improvement." Measured R@1 gain was +55% (0.600 → 0.933) from adding the re-ranker on top of hybrid. The completeness score jump (+0.333) confirmed that promoting the right chunk to rank 1 directly improves answer quality — the LLM pays more attention to earlier context.

**Qwen3.6-35B as both generator and judge worked well.** `/no_thinking` prefix gave clean JSON judge output. Mean faithfulness score of 5.0/5 across all configs suggests the generation prompt with company/section citation instruction is effective. The judge's reasoning explanations were specific and useful (e.g., noting a missing "cost of funding" detail rather than generic feedback).

**Homelab inference stack was reliable throughout.** Both the embedding server (port 8081) and the generation server (port 8082) were available for every phase without interruption. OpenAI-compatible API interface meant the same client code works for both.

---

## What Was Harder Than Expected

**EDGAR HTML extraction required custom tooling.** The initial plan assumed pdfplumber for PDFs. Reality: EDGAR's `submissions.json` API returns inline XBRL `.htm` files. The first ~15% of each file is garbled XBRL namespace data (`http://fasb.org/us-gaap/2025#...`). Building a custom `HTMLParser` subclass with `_is_xbrl_noise()` was necessary and took significant time. This is not documented in most RAG tutorials.

**Section detection was fragile across issuers.** The Item header regex (`^Item\s+\d+[A-Za-z]?\.\s+...`) matched single-line content headers correctly but missed Citigroup and Morgan Stanley's `1.` / `1A.` format. Both filings ended up with `section_title = "DOCUMENT"` for all chunks — no Item-level granularity. Workaround: excluded those two companies from single-source eval questions.

**Wells Fargo filing was a TOC index, not the actual 10-K.** The `primaryDocument` from Wells Fargo's EDGAR submission pointed to an 86KB index page rather than the full 10-K body (8–15MB for complete filings). Result: 24 chunks vs 400–660 for other companies. Discovered late — would add a content-length validation check to `download_filings.py` in a future version.

**Python 3.9.7 type hint compatibility.** The conda environment is Python 3.9.7. Any `X | None` or `list[str]` type hints (PEP 604 / PEP 585) cause runtime `TypeError`. Caught this after the first runtime failure — switched all type hints to `Optional[X]` and `List[X]` from `typing`. A project-level `pyproject.toml` specifying `python_requires = ">=3.9,<3.10"` would have caught this earlier.

**`DB_CONFIG` at import time gotcha.** In `embed_and_store.py`, `DB_CONFIG` is a module-level dict computed at import time. Any module that imports after setting env vars gets stale values. Documented in HANDOFF.md as a gotcha; retrieval code was written to read env at call time to avoid reproducing the issue.

---

## Key Technical Learnings

**No stemming for regulatory text BM25.** The tokenizer `re.findall(r"\b\w+\b", text.lower())` with no stemming was the right choice. Financial regulatory terms like "Rule 17a-4", "TLAC", "SCB", "LCR", "HQLA" should not be stemmed — "liquidating" and "liquidity" are different things in a risk disclosure context. Stemming would conflate terms that regulators deliberately distinguish.

**Cross-encoder as R@1 optimizer, not R@5 optimizer.** The re-ranker's most important function is putting the best chunk at position 1, not just surfacing it in the top-5. The LLM's attention mechanism reads context sequentially — the first chunk in the prompt gets more weight than the fifth. R@1 is therefore more predictive of answer quality than R@5 for generation tasks.

**RRF k=60 worked out-of-the-box.** No tuning was needed. The Cormack et al. (2009) default constant transferred directly to this corpus without modification. This confirms the ADR-003 rationale: RRF's strength is precisely that it requires no labeled data to tune.

**LLM judge JSON output needs a fallback.** The `_extract_json()` function in `judge.py` strips markdown fences before `json.loads()`. Even with `/no_thinking` and explicit instructions, a small fraction of responses could wrap JSON in triple backticks. The regex strip + fallback neutral score (3,3,3) prevents eval run failures from corrupting the results file.

**EDGAR ingestion order matters for eval set design.** Because Citigroup and Morgan Stanley have degraded section metadata, multi-source questions that include these companies work at the content level but not at the citation precision level. The eval set was designed to avoid questions requiring section-level filtering for these two companies. Future versions should fix the section regex before building the eval set.

---

## What Would Be Done Differently

1. **Validate EDGAR files before ingestion.** Add a content-length check (< 200KB = likely TOC wrapper) and a section detection check (< 3 sections detected = likely non-standard format) before embedding. Both issues (Wells Fargo TOC, Citigroup/Morgan Stanley section format) would have been caught before the 15-minute embedding run.

2. **Add minimum token count filter before cross-encoder re-ranking.** The one R@1 failure in Phase 4 (Q011) was caused by a cross-reference stub (table of contents entry, ~15 tokens) scoring higher than the actual content chunk. A filter of `len(c.content.split()) > 30` before passing to the cross-encoder would fix this class of failure.

3. **Commit `.gitignore` before first file creation.** `data/raw/` and `.env` appeared in `git status` before `.gitignore` was created. No data was committed accidentally, but it was a close call. The `.gitignore` should be the first commit in any new project.

4. **Use `python-dotenv`.** The manual `.env` loading boilerplate (`for line in open('.env')...`) appears in five files. It works but is fragile (no quoted value support, no `KEY=` without value support). `python-dotenv` was in `requirements.txt` but not installed in the conda env. Worth adding at project start.

5. **Ship a `pytest` smoke test suite at end of each phase.** No automated tests exist — verification was done by running scripts and inspecting output. For a career artifact, having a `tests/` directory with basic integration tests (can we connect to DB, does retrieval return at least 3 results, does judge return valid JSON) would make the project more reviewable.

---

## Deliverables Checklist

| Deliverable | Status | Location |
|-------------|--------|---------|
| Working retrieval API | ✅ Complete | `src/retrieval/api.py` — Flask, `/search` + `/search/dense` |
| Chunking strategy writeup | ✅ Complete | `docs/design/chunking-decision.md` |
| Eval set 20+ Q&A pairs | ✅ Complete | `eval/ground_truth.json` — 20 questions |
| Automated eval pipeline | ✅ Complete | `src/eval/run_eval.py` — 3 configs × 15 questions |
| All 5 ADRs complete | ✅ Complete | `docs/adr/ADR-001` through `ADR-005` — all Decided |
| Before/after eval scores | ✅ Complete | ADR-003: hybrid R@1=0.933 vs dense R@1=0.533; ADR-004: re-ranker R@1=0.933 vs no-reranker R@1=0.600 |

All acceptance criteria from `docs/SRS.md` met.

---

## Final Score Summary

| Phase | Key Metric | Result |
|-------|-----------|--------|
| Phase 1 — Ingestion | Chunks embedded | 3,332 / 9 companies |
| Phase 2 — Retrieval | API endpoint | Live on port 8080 |
| Phase 3 — Eval Set | In-scope R@5 (hybrid) | **1.000** |
| Phase 4 — LLM Judge | Mean score (hybrid) | **4.600 / 5** |
| Phase 4 — Ablation | Hybrid vs dense R@1 delta | **+0.400** |
| Phase 4 — Ablation | Re-ranker R@1 delta | **+0.333** |
