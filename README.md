# AI Platform Portfolio

A structured portfolio of five AI engineering projects built for professional development and career advancement toward a **Senior AI Engineer / AI Architect** role in regulated-industry environments (financial services, enterprise SaaS).

Each project targets a distinct layer of the AI stack. Together they tell a single coherent story: designing, evaluating, and securing an enterprise AI assistant built on top of Jira and Confluence.

---

## The Thread

All five projects share a common system under test — a **Jira/Confluence AI Help Desk Tool**: an LLM-powered assistant that handles IT and process requests by searching Confluence, creating Jira tickets, and escalating to humans when needed. This grounds every project in a realistic enterprise context rather than toy examples.

```
P01  →  How do you retrieve the right information?         (RAG pipeline over regulatory documents)
P02  →  How do you govern cost across teams?               (LLM gateway with per-team budget enforcement)
P03  →  How do you build a reliable agent?                 (3-agent pipeline with MCP tool use)
P04  →  How do you know it works?                          (Eval framework with CI gates)
P05  →  How do you secure it in a regulated environment?   (STRIDE threat model + compliance controls)
P06  →  Do the controls actually work in the pipeline?     (Integration layer composing P03 + P05)
```

---

## Projects

### [Project 01 — RAG Architecture](./project-01-rag-architecture/)
**Skill area:** Retrieval-augmented generation · **Status:** Complete

Builds a RAG pipeline over 9 real SEC 10-K filings from EDGAR. Focus is retrieval quality — not just ingestion. Compares three chunking strategies (fixed-size, semantic, hierarchical), implements pgvector with hybrid BM25+dense retrieval and RRF fusion, adds a cross-encoder re-ranker, and proves the improvement with a 3-config LLM-as-judge ablation (dense-only R@1=0.533 → hybrid+reranker R@1=0.933).

**Stack:** Python · pgvector (Docker) · `nomic-embed-text` (self-hosted) · `rank_bm25` · `cross-encoder/ms-marco-MiniLM-L-6-v2` · Qwen3-35B (self-hosted)

**Key artifacts:** Chunking strategy decision writeup · hybrid retrieval design doc · 20-question eval dataset with ground truth · `eval/results/phase4_lm_judge_scores.json` (3-config ablation) · 5 ADRs · retrospective

---

### [Project 02 — LLM Gateway / Cost Governance](./project-02-llm-gateway/)
**Skill area:** Cost governance · observability · multi-backend routing · **Status:** Complete

Builds a working Python gateway that sits in front of LLM backends (local llama.cpp, OpenAI-compatible), enforces per-team token budgets across three enforcement modes (hard block, soft cap, downgrade), logs structured JSON per request, emits Prometheus metrics, and exposes a cost dashboard. Includes all four routing strategies and a structured build-vs-buy comparison of Bifrost and LiteLLM — including the shadow routing gap that only the custom build closes.

**Stack:** FastAPI · SQLite · `tiktoken` · YAML config · Prometheus

**Key artifacts:** Working gateway (`gateway/`) with quota, routing, metrics, auth · `gateway.db` · Bifrost vs LiteLLM comparison · 4 ADRs · SRS

---

### [Project 03 — Agentic Systems & MCP](./project-03-agentic-mcp/)
**Skill area:** Multi-agent systems · MCP protocol · tool use · **Status:** Complete

Builds a full 3-agent pipeline (Planner → Researcher → Synthesizer) wired to real MCP servers. Custom Python MCP servers for SearXNG web search and GitHub REST API. Implements typed handoff schemas, tool error handling for all 5 failure classes, loop prevention, and resumable serialized pipeline state. Runs 5 deliberate failure-mode experiments — budget exhaustion, garbage tool output, ambiguous planner input, mid-run kill + resume, context overflow — each documented with root cause and production mitigation.

**Stack:** Python · `mcp` SDK · `openai` AsyncClient → self-hosted Qwen3-35B · SearXNG · GitHub REST API · Pydantic

**Key artifacts:** Full pipeline (`planner.py`, `researcher.py`, `synthesizer.py`, `orchestrator.py`) · Custom MCP servers · `ToolResult` error wrapper · `experiments/` (5 failure scenarios) · `state/exp4_d7fa13.json` (resume evidence) · `docs/lessons_learned.md` · 6 ADRs · HANDOFF.md

---

### [Project 04 — AI Observability & Evals](./project-04-observability-evals/)
**Skill area:** Eval engineering · CI integration · production monitoring · **Status:** Complete

Builds a full eval framework for the Jira/Confluence AI tool. 19-behavior inventory (11 P0), 30-case eval dataset across 6 scenario categories, versioned LLM-as-judge pipeline, CI workflow with cache-based baseline comparison and PR comment reporting, configurable regression gates, and a production monitoring design with 5-tier sampling strategy.

**Stack:** Python · Claude API (`claude-haiku-4-5` SUT, `claude-sonnet-4-6` judge) · GitHub Actions · DogStatsD · `gates.yaml`

**Key artifacts:** `eval/dataset.json` (30 cases) · `eval/prompts/judge_v1.md` (versioned judge prompt) · `.github/workflows/eval.yml` · `eval/gates.yaml` · production monitoring design

---

### [Project 05 — Enterprise Security & Compliance](./project-05-security-compliance/)
**Skill area:** LLM threat modeling · security controls · regulatory compliance · **Status:** Complete

Produces a formal threat model for the Jira/Confluence AI assistant adapted from STRIDE to the LLM attack surface. 22 threats across all 6 STRIDE categories, 22 controls across 5 layers, two working Python implementations with 55 passing tests, and full compliance mapping to SEC Rule 17a-4(f), FINRA Rule 4511, and SOC 2 Type II — 0 gaps.

**Stack:** Python · Presidio (PII detection) · `pytest` · SOC 2 / SEC 17a-4 / FINRA 4511

**Key artifacts:** `THREAT-MODEL-001.md` (22 threats) · `GUARDRAILS-MATRIX-001.md` (22 controls) · `src/content_isolation.py` · `src/pii_scanner.py` · `COMPLIANCE-MAP-001.md`

---

### [Project 06 — Integration: Secure Agentic Pipeline](./project-06-integration-mcp-security/)
**Skill area:** Cross-project integration · security middleware composition · **Status:** Complete

Closes P05's core weakness: controls verified in isolation but never exercised in the actual pipeline. Wires P05's `content_isolation.py` and `pii_scanner.py` into P03's 3-agent pipeline as active middleware, with zero modifications to either parent project. Demonstrates that independently verified components compose correctly — and documents exactly where they don't yet (the pre-LLM hook architectural gap, deferred per ADR-002).

**Stack:** Python · `pytest` · `unittest.mock` · uv · P03 (editable dep) · P05 (sys.path injection)

**Key artifacts:** `p06/secure_researcher.py` (SecureResearcherAgent, SecureOrchestrator, PIIInFindingError) · 53/53 tests passing (injection defense, PII scan on real ResearchFinding, full pipeline regression) · `docs/integration-surface.md` (break-surface tables per wiring point) · `docs/lessons-learned.md` (4 bugs unit tests missed, P02 gateway wiring path) · SRS-001 · DESIGN-001 · ADR-001 through ADR-003

---

## Infrastructure

Projects run against a self-hosted homelab rather than cloud-only dependencies:

| Service | URL | Used by |
|---|---|---|
| Embedding model (`nomic-embed-text`) | `ai.scheidy.com:8081` | P01 |
| LLM inference (Qwen3-35B, llama.cpp) | `ai.scheidy.com:8082` | P03 |
| Web search (SearXNG) | `search.scheidy.com` | P03 |
| Vector store (pgvector, Docker) | `localhost:5433` | P01 |

---

## Documentation Conventions

Every project follows the same structure:

| File | Purpose |
|---|---|
| `project-0N-[name].md` | Project brief — scope, phases, deliverables |
| `findings.md` | Research notes and decisions as they accumulate |
| `progress.md` | Session-by-session log with test results |
| `task_plan.md` | Phase tracker with status |
| `docs/adr/` | Architecture Decision Records for every major choice |
| `INDEX.md` | Living artifact index with rollup checklist (P06 pattern, backfill planned for P01–P05) |
| `HANDOFF.md` | Resume context — current state, gotchas, exact next action |

---

## Portfolio Review

A full written analysis of each project — individual assessment and cross-project synthesis — is in [`PORTFOLIO-REVIEW.md`](./PORTFOLIO-REVIEW.md). It includes a completion snapshot and prioritized next steps for finishing the portfolio.
