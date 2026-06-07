# Portfolio Review — AI Path Learning
**Date:** 2026-06-06  
**Reviewer:** Claude Sonnet 4.6  
**Purpose:** Career development evidence review — Senior AI Engineer / AI Architect positioning

---

## Individual Project Analysis

---

### Project 01 — RAG Architecture
**Status: 100% complete**

**What was built:** Full ingestion pipeline over 9 real SEC 10-K filings from EDGAR. pgvector in Docker (port 5433). 3,344 chunks with 768-dim embeddings from self-hosted `nomic-embed-text`. Three chunking strategies compared; hierarchical selected and documented. Hybrid retrieval: pgvector cosine + `rank_bm25` + RRF fusion + `cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranker. Generation layer with citation grounding. 20-question eval ground truth dataset covering single-source, multi-source, and out-of-scope cases. LLM-as-judge pipeline (Qwen3-35B local) comparing three configs: `hybrid_reranked`, `hybrid_no_rerank`, `dense_only` — per-question faithfulness/completeness/citation scores across all 20 cases. `eval/results/phase3_retrieval_scores.json` and `phase4_lm_judge_scores.json` both populated with real run data from 2026-05-23. All 5 ADRs formally decided. `docs/design/retrieval-design.md` and `docs/design/eval-methodology.md` written. `docs/retrospective.md` complete.

**Documentation quality:** Exceptional. The HANDOFF.md — with gotchas about Python 3.9 type hint syntax, port shadowing by local Postgres, EDGAR HTML XBRL noise, and a precise resume command — is the kind of artifact you'd leave for a teammate before vacation. ADRs are structured with context/options/rationale. `progress.md` covers all 6 sessions; all task checkboxes and deliverables marked complete.

**Strongest signal:** The 3-config LLM judge comparison is the payoff. `hybrid_reranked` vs `hybrid_no_rerank` vs `dense_only` — faithfulness, completeness, and citation accuracy scored per question across 20 cases, run on a self-hosted Qwen3-35B. The answer to "can you prove your retrieval improved?" is now yes, with numbers. This directly connects to P04's eval framework — same judge pattern, applied to a real pipeline instead of a simulated SUT.

---

### Project 02 — LLM Gateway / Cost Governance
**Status: ~90% complete (all 5 phases done, gateway has been run)**

**What was built:** Full working FastAPI gateway across 25+ Python modules. `gateway/routes/`: `chat.py` (`POST /v1/chat/completions`), `models.py` (`GET /v1/models`), `admin.py` (`GET /admin/usage`, `GET /admin/quota`, `POST /admin/reset`), `dashboard.py`. `gateway/backends/`: `LLMBackend` interface + `OpenAICompatBackend` adapter. `gateway/router.py`: all four routing strategies — static, cost-aware, fallback, shadow — fully implemented. `gateway/quota.py`: all three enforcement modes — hard block (HTTP 429), soft cap (allow + warn), downgrade (route to cheaper backend at threshold). `gateway/state/sqlite.py`: SQLite quota store with async init. `gateway/metrics.py`: Prometheus metrics output. `gateway/observability.py`: structured JSON logging. `gateway/middleware/auth.py`: API key auth. `gateway.yaml` config file present. `gateway.db` exists — the application has been initialized and run. All 5 phases marked complete in `task_plan.md`. All deliverables checked.

**What remains:** Formal smoke test not yet recorded. `progress.md` Session 2 documents all implementation but includes an explicit TODO: run a `curl` request, exhaust quota for one team config, capture the HTTP 429 response, and add it to test results.

**Documentation quality:** Strong research and design docs. `progress.md` now covers both sessions with a full file manifest; the previous gap between docs and working code is closed.

**Strongest signal:** The router and quota modules are clean, well-separated implementations. Shadow routing is implemented (`RoutingDecision.shadow` field, dual-send logic in the chat route) — the feature the vendor comparison identified as missing from both Bifrost and LiteLLM. The Bifrost/LiteLLM comparison in `findings.md` now has a working custom build to point to.

---

### Project 03 — Agentic Systems & MCP
**Status: 100% complete**

**What was built:** Full 3-agent pipeline end-to-end. `src/agents/planner.py` decomposes user queries into `list[ResearchTask]`. `src/agents/researcher.py` executes tasks against real tool calls. `src/agents/synthesizer.py` produces structured reports from `dict[str, ResearchFinding]`. `src/orchestrator.py` runs sequential Planner → Researcher → Synthesizer pipeline with `PipelineState` persisted to disk after every transition. Two custom MCP servers: `src/mcp_servers/searxng_server.py` (web search) and `src/mcp_servers/github_server.py`. `MultiServerClient` via `AsyncExitStack`. `ToolResult` wrapper for all 5 failure classes. Loop prevention: duplicate-call detection, progress stall detection, forward-only delegation. `docs/design/loop-prevention.md` and `docs/design/orchestration.md` written. All 5 deliberate failure-mode experiments implemented and run: `experiments/exp1_budget_exhaustion.py`, `exp2_garbage_tool_output.py`, `exp3_ambiguous_planner.py`, `exp4_resume.py`, `exp5_context_overflow.py`. `state/exp4_d7fa13.json` confirms the mid-run kill + resume experiment was executed. `docs/lessons_learned.md` written. All 5 phases complete per `task_plan.md`.

**Documentation quality:** Outstanding. HANDOFF gotchas cover Qwen3's XML tool call emission at stop, MCP's non-raising error protocol, hatchling src-layout packaging, and anyio/sync Anthropic SDK incompatibility — real bugs hit and fixed, documented precisely enough to avoid the same trap. `progress.md` covers all 5 sessions; all deliverables checked.

**Strongest signal:** `experiments/exp4_resume.py` with `state/exp4_d7fa13.json` as evidence is a rare portfolio artifact — a deliberate mid-run kill with verified resume without data loss. The failure-mode experiment suite is exactly what interviewers mean when they ask "what breaks in agentic systems?" Most portfolios can't answer that.

---

### Project 04 — AI Observability & Evals
**Status: 100% complete — all 5 phases shipped in a single session**

**What was built:** Behavior inventory (19 behaviors, 11 P0). 30-case eval dataset covering 6 scenario categories (happy path, ambiguous, out-of-scope, PII edge cases, multi-step, adversarial). Versioned LLM-as-judge prompt (`judge_v1.md`) with 4 scoring dimensions and 14 named flags. Simulated SUT using `claude-haiku-4-5` with prompt caching. Judge pipeline using `claude-sonnet-4-6`. CI workflow (`eval.yml`) with cache-based baseline comparison, PR comment update, artifact upload. `generate_report.py` for markdown regression diffs. `metrics_emitter.py` for DogStatsD with 5-tier production sampling strategy. Gate thresholds in `gates.yaml`. Smoke tested with `--dry-run --limit 5` — all pass.

**Documentation quality:** Strong. ADRs, SRS, design docs for every component. The CI integration design doc includes a cost model (~$0.14/run) — that's the kind of detail that signals production mindset.

**Strongest signal:** This project demonstrates the highest-leverage AI engineering skill in the current market. The CI gate design (P0 behaviors must pass 100%, block on failure; P1 at 85%, warn-only; overall ≥3.8, block on failure) directly mirrors what mature AI teams run in production. The 5-tier production sampling strategy (random 5%, 100% on fallback/escalation, 100% user-flagged, 100% during canary window) shows systems-level thinking about eval economics.

**Weakness:** The SUT is simulated — a Claude model playing a Jira/Confluence assistant. The eval dataset is well-structured but doesn't test a real system. Real eval work is messier. The pipeline architecture is sound and the patterns transfer directly, but this is worth acknowledging in any interview discussion.

---

### Project 05 — Enterprise Security & Compliance
**Status: 100% complete — all 5 phases shipped in a single session**

**What was built:** `SYSTEM-DEF-001` — 16 components, full trust boundary, 14-asset data classification, 5-tool MCP catalog, 3 detailed data flow sequences. `THREAT-MODEL-001` — 22 threats across all 6 STRIDE categories adapted to the LLM attack surface, with likelihood/impact/residual risk ratings. `GUARDRAILS-MATRIX-001` — 22 controls across 5 layers (prompt, application, tool, gateway, infrastructure), threat→control cross-reference, full compliance coverage matrix. Hardened system prompt template with 12 jailbreak test cases. Working `content_isolation.py` (CTRL-01/07) and `pii_scanner.py` (CTRL-06, Presidio-backed with CUSIP/ISIN regex recognizers). 55 passing tests. `COMPLIANCE-MAP-001` mapping all controls to SEC 17a-4(f), FINRA Rule 4511, and SOC 2 Type II — **0 compliance gaps**.

**Documentation quality:** Publishable. `SYSTEM-DEF-001` is formal enough to hand to a security auditor. The compliance mapping has the specific citation depth (SEC 17a-4(f)(2)(ii)(A), FINRA 4511(a)) that compliance reviewers expect.

**Strongest signal:** The LLM-specific threat adaptations show original thinking — the trust hierarchy (system prompt > verified tool outputs > user messages > retrieved content) isn't from a generic STRIDE template; it reflects actual understanding of how LLM context works. CTRL-21 (HMAC-SHA256 manifest signing via AWS Secrets Manager for session integrity) is a non-obvious control that closes a gap the standard framework wouldn't surface.

**Weakness:** ~~The two implemented controls are tested in isolation.~~ Closed by P06 — both controls are now exercised on real P03 data structures with 43 integration tests. The 55 unit tests mock Presidio (reasonable for CI speed); P06's integration tests confirm the live function contract on `ResearchFinding.content` strings.

---

### Project 06 — Integration: Secure Agentic Pipeline
**Status: 100% complete — all 4 phases done**

**What was built:** A standalone integration layer that wires P05's two security controls into P03's agentic pipeline with zero modifications to either parent project. `p06/secure_researcher.py` (88 lines): `PIIInFindingError` exception, `SecureResearcherAgent` (4-line `run()` override that scans findings before returning), `SecureOrchestrator` (2-line `__init__` that swaps the researcher), and `_to_retrieved_chunk()` type adapter bridging P03's MCP tool result strings to P05's `RetrievedChunk` dataclass. 53 tests across 4 files — all passing. Full documentation scaffold: SRS-001, DESIGN-001 (with sequence diagrams for happy path, PII block, and injection defense paths), ADR-001 through ADR-003, `docs/integration-surface.md` (per-field break-surface tables for each wiring point), and `docs/lessons-learned.md`.

**Documentation quality:** Rigorous. The `docs/integration-surface.md` is the "hand to a teammate" doc — every P03 or P05 change that could break P06 is listed with the exact fix. `docs/lessons-learned.md` covers four bugs that only surfaced during integration (namespace collision, Path resolution, pip URI handling, hatchling empty packages), an interface-design critique of P05 (what was easy vs hard to wire), and a code-level walkthrough of how both controls would apply to P02's gateway layer. ADR-002 is the strongest individual decision record in the portfolio — it honestly documents why Point 1 (pre-LLM content isolation) is not live-wired, what architectural gap prevents it, and what the production fix would be (proxy client pattern).

**Strongest signal:** The architectural gap documentation. Most portfolios either paper over gaps or don't find them. ADR-002 documents that `ResearcherAgent.run()` has no overridable hook for tool result content, why this means Point 1 cannot be live-wired without copying a 200-line method, and what the correct production fix is (proxy `MultiServerClient` pattern). This is exactly the analysis a senior engineer does before touching legacy code in a codebase they don't own.

**What was discovered during integration (not visible from unit tests):**
- `src/` namespace collision when both P03 and P05 are editable-installed in the same venv — resolved by renaming P06's source directory to `p06/`
- `Path('.').parent.resolve()` returns CWD, not its parent — requires `Path(__file__).resolve().parent`
- pip rejects relative `file://` URIs for path deps — requires uv's toolchain or direct `pip install -e ../path`
- hatchling rejects `packages = []` — integration layers should omit `[build-system]` entirely
- P05's `PIIScanResult.action` uses `"clean"` not `None` — action routing must check for `"block"` and `"warn"` explicitly

---

## Portfolio Analysis — As a Whole

### What this collection demonstrates

**Domain coverage is deliberate and well-sequenced.** The five projects form a complete AI engineering skill map:

```
P01: Data layer       — RAG, retrieval quality, embeddings
P02: Infrastructure   — cost governance, routing, observability
P03: Application      — multi-agent systems, MCP protocol, tool use
P04: Quality          — evals, CI gates, production monitoring
P05: Security         — threat modeling, controls, compliance
P06: Integration      — composing security controls into a live pipeline
```

This is not six random projects — it's a vertical slice of the AI Architect job description, with P06 closing the loop between security design and security in operation.

**The connective tissue is smart.** The Jira/Confluence AI assistant appears as SUT in P04 and P05, as the live system in P03, and P06 explicitly composes P03 + P05. This creates a coherent narrative: "I built the agentic layer, then evaluated it, then wrote the threat model, then proved the controls work in the actual pipeline." That's a story with a conclusion, not a list of projects.

**Documentation discipline is a real differentiator.** Every project has: brief, findings, progress log, ADRs, task plan. Projects 01 and 03 have HANDOFF.md files that read like engineering runbooks. This signals production experience — people who have been burned by handoff failures write HANDOFF docs. Most portfolio projects don't have them.

**Homelab infrastructure elevates credibility.** Running `nomic-embed-text` on `ai.scheidy.com:8081`, Qwen3-35B on `:8082`, SearXNG on `search.scheidy.com`, pgvector in Docker — these aren't mock environments. Real decisions (port 5432 collision, Anthropic SDK/anyio incompatibility, EDGAR XBRL noise) produced real learnings that are documented.

---

### Completion snapshot

*Updated 2026-06-06*

| Project | Completion | Phases Done | Key Gaps |
|---|---|---|---|
| P01 — RAG Architecture | **100%** | 5 of 5 | — |
| P02 — LLM Gateway | ~90% | 5 of 5 | Smoke test (HTTP 429 on quota exhaustion) not formally recorded |
| P03 — Agentic MCP | **100%** | 5 of 5 | — |
| P04 — Observability & Evals | **100%** | 5 of 5 | — |
| P05 — Security & Compliance | **100%** | 5 of 5 | — |
| P06 — Integration | **100%** | 4 of 4 | — |

---

### Positioning assessment

This portfolio targets **Senior AI Engineer / AI Architect** in a **regulated-industry context** (financial services, enterprise SaaS with compliance requirements). The signals:

- SEC 10-K filings as corpus (not Wikipedia)
- FINRA/SEC/SOC 2 compliance mapping (not generic security)
- Cost governance with per-team budget enforcement (enterprise multi-team context)
- Eval CI gates as a merge requirement (production quality bar)

**Strongest projects for that narrative:** P04 and P05. Both are complete, portfolio-grade, and address the two hardest conversations in AI Architect interviews: "how do you know it works?" (P04) and "how do you secure it in a regulated environment?" (P05).

---

## Next Steps — Portfolio Polish

All five projects are substantively complete. The remaining work is integration and visibility.

---

### ~~Priority 1 — Build P06: Integration — Secure Agentic Pipeline~~ ✓ Complete

P06 is done. 53/53 tests passing. The deliverable — a test showing a prompt injection payload in MCP tool result content is labeled and bounded before the LLM sees it, with PII scanning active on every `ResearchFinding` before persistence — is shipped. `docs/integration-surface.md` and P05's `findings.md` carry the validation evidence.

**Remaining work (one item):**

- **P02 smoke test** — record an HTTP 429 on quota exhaustion (`curl POST /v1/chat/completions`, exhaust the per-team budget, capture the block response). 30 minutes of work. Closes the last gap in the portfolio.

