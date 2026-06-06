# AI Path Learning

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
```

---

## Projects

### [Project 01 — RAG Architecture](./project-01-rag-architecture/)
**Skill area:** Retrieval-augmented generation · **Status:** Phase 1 complete (ingestion)

Builds a RAG pipeline over 9 real SEC 10-K filings from EDGAR. Focus is retrieval quality — not just ingestion. Compares three chunking strategies (fixed-size, semantic, hierarchical), implements pgvector with hybrid BM25+dense retrieval and RRF fusion, adds a cross-encoder re-ranker, and measures the improvement via LLM-as-judge scoring.

**Stack:** Python · pgvector (Docker) · `nomic-embed-text` (self-hosted) · `rank_bm25` · `cross-encoder/ms-marco-MiniLM-L-6-v2` · Claude API

**Key artifacts:** Chunking strategy decision writeup · 5 Architecture Decision Records · Eval dataset with ground truth chunk references

---

### [Project 02 — LLM Gateway / Cost Governance](./project-02-llm-gateway/)
**Skill area:** Cost governance · observability · multi-backend routing · **Status:** Design + research complete

Designs and partially builds a Python gateway that sits in front of LLM backends (Bedrock, local llama.cpp, OpenAI-compatible), enforces per-team token budgets, logs usage, and exposes a cost dashboard. Includes a structured build-vs-buy comparison of Bifrost and LiteLLM.

**Stack:** FastAPI · SQLite / Redis · `tiktoken` · YAML config · Datadog

**Key artifacts:** Architecture design doc · Bifrost vs LiteLLM comparison (with atomic quota enforcement analysis) · 4 ADRs · SRS

---

### [Project 03 — Agentic Systems & MCP](./project-03-agentic-mcp/)
**Skill area:** Multi-agent systems · MCP protocol · tool use · **Status:** Phase 2 complete (Researcher agent)

Builds a 3-agent pipeline (Planner → Researcher → Synthesizer) wired to real MCP servers. Custom Python MCP servers for SearXNG web search and GitHub REST API. Implements typed handoff schemas, tool error handling for all 5 failure classes, loop prevention, and serializable pipeline state. Designed as a deliberate stress-test of multi-agent failure modes.

**Stack:** Python · `mcp` SDK · `openai` AsyncClient → self-hosted Qwen3-35B · SearXNG · GitHub REST API · Pydantic

**Key artifacts:** Working Researcher agent (end-to-end validated) · Custom MCP servers · `ToolResult` error wrapper · 6 ADRs · HANDOFF.md

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
| `HANDOFF.md` | Resume context — current state, gotchas, exact next action |

---

## Portfolio Review

A full written analysis of each project — individual assessment and cross-project synthesis — is in [`PORTFOLIO-REVIEW.md`](./PORTFOLIO-REVIEW.md). It includes a completion snapshot and prioritized next steps for finishing the portfolio.
