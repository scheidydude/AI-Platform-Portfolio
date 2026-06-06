# Portfolio Review — AI Path Learning
**Date:** 2026-06-06  
**Reviewer:** Claude Sonnet 4.6  
**Purpose:** Career development evidence review — Senior AI Engineer / AI Architect positioning

---

## Individual Project Analysis

---

### Project 01 — RAG Architecture
**Status: ~30% complete (Phase 1 of 5 done, handed off mid-build)**

**What was built:** Full ingestion pipeline over 9 real SEC 10-K filings from EDGAR. pgvector running in Docker (port 5433). 3,344 chunks in DB with 768-dim embeddings from a self-hosted `nomic-embed-text` model. Three chunking strategies implemented and compared; hierarchical chunking selected and documented. Dense retrieval verified with a real query. 5 ADR stubs created (2 formally decided).

**What remains:** Hybrid retrieval (`rank_bm25` + RRF fusion), cross-encoder re-ranker, generation layer, 20+ eval case ground truth dataset, LLM-as-judge pipeline. These are the harder, higher-value phases.

**Documentation quality:** Exceptional. The HANDOFF.md alone — with gotchas about Python 3.9 type hint syntax, port shadowing by local Postgres, EDGAR HTML XBRL noise, and a precise resume command — is the kind of artifact you'd leave for a teammate before vacation. ADRs are structured with context/options/rationale.

**Strongest signal:** The decision to build a custom HTML extractor with an XBRL noise filter rather than use BeautifulSoup shows real judgment — not just following a tutorial. The chunking strategy writeup (why hierarchical beats fixed-size for regulatory text, with specific failure modes of the alternatives) is portfolio-quality reasoning.

**Weakness:** The most impressive parts of RAG — retrieval quality measurement, before/after eval scores, the LLM-as-judge — are not built. If someone asks "can you prove your retrieval improved?" the answer is currently no.

---

### Project 02 — LLM Gateway / Cost Governance
**Status: ~20% complete (scaffolding + research, no working gateway)**

**What was built:** FastAPI project structure. Full documentation scaffold: SRS, architecture design doc, 4 ADRs (FastAPI, SQLite→Redis migration strategy, tiktoken reconciliation, YAML team config). A detailed vendor comparison analysis (Bifrost vs LiteLLM) that surfaced real tradeoffs — LiteLLM wins on cost governance and SSO, Bifrost wins at >5000 RPS where Python overhead matters, shadow routing is only in the custom build.

**What remains:** The actual gateway code. No working route, no end-to-end request, no quota enforcement, no dashboard, no smoke test. Progress.md says Phase 1 is "complete — pending real end-to-end smoke test" but the smoke test was never done.

**Documentation quality:** Good research and design docs, but the gap between docs and working code is the widest of all five projects.

**Strongest signal:** The Bifrost/LiteLLM comparison in `findings.md` is genuinely sophisticated — atomic INCR race conditions in SQLite vs Redis for concurrent quota enforcement is the kind of detail that comes from building or deeply reading source. The shadow routing identification as a gap in both vendor tools is a sharp observation.

**Weakness:** No runnable artifact. This is the most documentation-forward, least evidence-forward project. Without a working gateway, the learning is primarily conceptual.

---

### Project 03 — Agentic Systems & MCP
**Status: ~40% complete (Researcher agent done, Planner/Synthesizer/Orchestrator not started)**

**What was built:** A fully working Researcher agent end-to-end validated with real tool calls. Two custom Python MCP servers (SearXNG for web search, GitHub REST API). `MultiServerClient` that spawns both servers as stdio subprocesses simultaneously via `AsyncExitStack`. `ToolResult` wrapper covering all 5 error classes including MCP protocol-level `isError` flag. All Pydantic schemas for handoff contracts. 6 accepted ADRs.

**What remains:** Planner agent, Synthesizer agent, Orchestrator, progress stall detection (duplicate-call detection exists but stall detection does not), state persistence, and the deliberate failure-mode experiments (Phase 5) which are the most valuable learning surface.

**Documentation quality:** Outstanding. The HANDOFF gotchas section specifically calls out: Qwen3's XML tool call emission at stop, MCP's non-raising error protocol, hatchling src-layout packaging, and the anyio/sync Anthropic SDK incompatibility. These are real bugs that were hit and fixed, documented precisely enough to avoid the same trap.

**Strongest signal:** Building custom MCP servers from scratch (SearXNG because the npm package was deprecated, GitHub because the Go binary wasn't installed) rather than stopping when the standard tools didn't work. This is evidence of real problem-solving, not tutorial execution.

**Weakness:** The three-agent pipeline — the stated goal — doesn't exist yet. The Researcher is solid, but without Planner decomposition and Synthesizer synthesis, this is one agent, not a pipeline. The failure-mode experiments (Phase 5) that are the project's primary learning objective haven't been run.

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

**Weakness:** The two implemented controls are tested in isolation. There's no integration test showing them functioning in the actual agentic pipeline from Project 3. The 55 tests mock Presidio rather than running the real analyzer — reasonable for CI speed, but understates integration risk.

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
```

This is not five random projects — it's a vertical slice of the AI Architect job description.

**The connective tissue is smart.** The Jira/Confluence AI assistant appears as SUT in P04 and P05, and as design context in P03. This creates a coherent narrative: "I built evaluation and security frameworks for an enterprise AI tool I also built the agentic layer for." That's a story, not a list of projects.

**Documentation discipline is a real differentiator.** Every project has: brief, findings, progress log, ADRs, task plan. Projects 01 and 03 have HANDOFF.md files that read like engineering runbooks. This signals production experience — people who have been burned by handoff failures write HANDOFF docs. Most portfolio projects don't have them.

**Homelab infrastructure elevates credibility.** Running `nomic-embed-text` on `ai.scheidy.com:8081`, Qwen3-35B on `:8082`, SearXNG on `search.scheidy.com`, pgvector in Docker — these aren't mock environments. Real decisions (port 5432 collision, Anthropic SDK/anyio incompatibility, EDGAR XBRL noise) produced real learnings that are documented.

---

### Completion snapshot

| Project | Completion | Phases Done | Key Gaps |
|---|---|---|---|
| P01 — RAG Architecture | ~30% | 1 of 5 | Hybrid retrieval, generation, eval scores |
| P02 — LLM Gateway | ~20% | Docs only | Any working gateway code |
| P03 — Agentic MCP | ~40% | 1–2 of 5 | Planner, Synthesizer, Orchestrator, failure experiments |
| P04 — Observability & Evals | **100%** | 5 of 5 | — |
| P05 — Security & Compliance | **100%** | 5 of 5 | — |

---

### Positioning assessment

This portfolio targets **Senior AI Engineer / AI Architect** in a **regulated-industry context** (financial services, enterprise SaaS with compliance requirements). The signals:

- SEC 10-K filings as corpus (not Wikipedia)
- FINRA/SEC/SOC 2 compliance mapping (not generic security)
- Cost governance with per-team budget enforcement (enterprise multi-team context)
- Eval CI gates as a merge requirement (production quality bar)

**Strongest projects for that narrative:** P04 and P05. Both are complete, portfolio-grade, and address the two hardest conversations in AI Architect interviews: "how do you know it works?" (P04) and "how do you secure it in a regulated environment?" (P05).

---

## Next Steps — Completing the Portfolio

Priority order based on return-on-effort and interview narrative value.

---

### Priority 1 — Finish P01 Phases 2–3 (highest ROI)

**Why first:** P01 is the most commonly asked-about skill area. Retrieval quality measurement is what separates "I did RAG" from "I can prove my RAG works." It also closes the loop with P04 — using the real eval framework on a real pipeline instead of a simulated SUT.

**Specific work:**

1. Build `src/retrieval/search.py` — hybrid search: pgvector cosine + `rank_bm25` + RRF fusion
2. Add `cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranker (CPU-viable on homelab)
3. Build `src/retrieval/api.py` — simple retrieval endpoint
4. Write `docs/design/retrieval-design.md`, update ADR-003 and ADR-004
5. Build `src/generation/` — prompt with citation grounding pattern
6. Write 20 Q&A eval cases with ground truth chunk references
7. Wire P04's judge pipeline to score P01's outputs — this is the "before/after" story
8. Record retrieval recall@K and faithfulness scores at baseline vs. after re-ranker

**Deliverable that matters:** A table showing retrieval recall@K and faithfulness before and after adding the re-ranker. Numbers that prove the improvement.

---

### Priority 2 — Finish P03 Phases 3–5 (completes the agent narrative)

**Why second:** P03 Phase 2 ending with a working Researcher is actually a strong stopping point for now. But to tell the full multi-agent story, you need the Planner and Synthesizer. Phase 5's deliberate failure-mode experiments are the most distinctive part — very few people document what breaks on purpose.

**Specific work:**

1. Mark Phase 2 complete in `task_plan.md` (stale)
2. Write `docs/design/loop-prevention.md`, then implement progress stall detection in `src/agents/researcher.py`
3. Build `src/agents/planner.py` — decomposes user request into `list[ResearchTask]`
4. Build `src/agents/synthesizer.py` — takes `dict[str, ResearchFinding]`, produces structured report
5. Build `src/orchestrator.py` — sequential pipeline, `PipelineState` persisted to disk after each transition
6. Run all 5 Phase 5 failure-mode experiments; document results in `findings.md`
7. Write `docs/lessons-learned.md` — what broke, root causes, how you'd address each in production

**Deliverable that matters:** A running end-to-end pipeline with a documented failure experiment showing the mid-run kill + resume. That's a rare artifact.

---

### Priority 3 — Get P02 to a working smoke test (close the credibility gap)

**Why third:** P02 is the only project with no working code. The research and design docs are strong, but a candidate who can explain Bifrost vs LiteLLM tradeoffs but has never run their own gateway is in a weaker position than one who has.

**Specific work — minimum viable:**

1. Implement `POST /v1/chat/completions` proxying to one backend (llama.cpp local is fine)
2. Implement `GET /admin/usage` reading from SQLite
3. Write one token count to SQLite per request
4. Implement hard-block quota enforcement for one team config
5. Run a request, hit the quota limit, verify HTTP 429
6. Add this smoke test result to `progress.md`

The full Phase 3 dashboard and Phase 4 multi-backend routing are nice-to-have. The smoke test result is the minimum that closes the gap.

---

### Priority 4 — Integration: wire P05 controls into P03's pipeline

**Why last:** High differentiation value but requires P03 to be complete first. The weakness in P05 is that the controls are tested in isolation. Showing `content_isolation.py` and `pii_scanner.py` running as middleware in the actual agentic pipeline connects the two projects into a coherent system.

**Specific work:**

1. Import `content_isolation.prepare_retrieved_context()` into P03's Researcher — wrap all retrieved content before injecting into LLM context
2. Import `pii_scanner.scan_output_for_pii()` into P03's Researcher — scan final finding content before writing to `state/`
3. Add a test case in P03 where a retrieved document contains an injection attempt — verify isolation holds
4. Document this in P05's `findings.md` as integration validation

**Deliverable that matters:** A test showing the injection attempt is neutralized by the content isolation wrapper. Connects the security paper to the working agent.

---

### Cross-cutting: one thing to do now

Before starting any of the above — push this repo to GitHub if it isn't already there, and add a `README.md` at the monorepo root that explains the five projects, the connective Jira/Confluence AI narrative, and links to each project's brief. Recruiters and hiring managers will land on the root first. The documentation inside each project is excellent; it needs a front door.
