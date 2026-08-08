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
P07  →  How do you safely execute untrusted agent code?    (gVisor sandboxed tool execution)
P08  →  How do you recover a long-running task mid-flight? (Firecracker microVM checkpoint/restore)
```

P07 and P08 extend the thread into a second system, **Orchid** — a self-hosted agent orchestration platform — rather than the Jira/Confluence assistant used by P01–P06. They target Staff+ infrastructure competencies (sandboxing, multi-tenant isolation, durable execution) not covered by the first six projects.

---

## Projects

### [Project 01 — RAG Architecture](./project-01-rag-architecture/)
**Skill area:** Retrieval-augmented generation · **Status:** Complete · [Doc index](./project-01-rag-architecture/INDEX.md)

Builds a RAG pipeline over 9 real SEC 10-K filings from EDGAR. Focus is retrieval quality — not just ingestion. Compares three chunking strategies (fixed-size, semantic, hierarchical), implements pgvector with hybrid BM25+dense retrieval and RRF fusion, adds a cross-encoder re-ranker, and proves the improvement with a 3-config LLM-as-judge ablation (dense-only R@1=0.533 → hybrid+reranker R@1=0.933).

**Stack:** Python · pgvector (Docker) · `nomic-embed-text` (self-hosted) · `rank_bm25` · `cross-encoder/ms-marco-MiniLM-L-6-v2` · Qwen3-35B (self-hosted)

**Key artifacts:** Chunking strategy decision writeup · hybrid retrieval design doc · 20-question eval dataset with ground truth · `eval/results/phase4_lm_judge_scores.json` (3-config ablation) · 5 ADRs · retrospective

---

### [Project 02 — LLM Gateway / Cost Governance](./project-02-llm-gateway/)
**Skill area:** Cost governance · observability · multi-backend routing · **Status:** Complete · [Doc index](./project-02-llm-gateway/docs/INDEX.md)

Builds a working Python gateway that sits in front of LLM backends (local llama.cpp, OpenAI-compatible), enforces per-team token budgets across three enforcement modes (hard block, soft cap, downgrade), logs structured JSON per request, emits Prometheus metrics, and exposes a cost dashboard. Includes all four routing strategies and a structured build-vs-buy comparison of Bifrost and LiteLLM — including the shadow routing gap that only the custom build closes.

**Stack:** FastAPI · SQLite · `tiktoken` · YAML config · Prometheus

**Key artifacts:** Working gateway (`gateway/`) with quota, routing, metrics, auth · `gateway.db` · Bifrost vs LiteLLM comparison · 4 ADRs · SRS

---

### [Project 03 — Agentic Systems & MCP](./project-03-agentic-mcp/)
**Skill area:** Multi-agent systems · MCP protocol · tool use · **Status:** Complete · [Doc index](./project-03-agentic-mcp/docs/index.md)

Builds a full 3-agent pipeline (Planner → Researcher → Synthesizer) wired to real MCP servers. Custom Python MCP servers for SearXNG web search and GitHub REST API. Implements typed handoff schemas, tool error handling for all 5 failure classes, loop prevention, and resumable serialized pipeline state. Runs 5 deliberate failure-mode experiments — budget exhaustion, garbage tool output, ambiguous planner input, mid-run kill + resume, context overflow — each documented with root cause and production mitigation.

**Stack:** Python · `mcp` SDK · `openai` AsyncClient → self-hosted Qwen3-35B · SearXNG · GitHub REST API · Pydantic

**Key artifacts:** Full pipeline (`planner.py`, `researcher.py`, `synthesizer.py`, `orchestrator.py`) · Custom MCP servers · `ToolResult` error wrapper · `experiments/` (5 failure scenarios) · `state/exp4_d7fa13.json` (resume evidence) · `docs/lessons_learned.md` · 6 ADRs · HANDOFF.md

---

### [Project 04 — AI Observability & Evals](./project-04-observability-evals/)
**Skill area:** Eval engineering · CI integration · production monitoring · **Status:** Complete · [Doc index](./project-04-observability-evals/docs/index.md)

Builds a full eval framework for the Jira/Confluence AI tool. 19-behavior inventory (11 P0), 30-case eval dataset across 6 scenario categories, versioned LLM-as-judge pipeline, CI workflow with cache-based baseline comparison and PR comment reporting, configurable regression gates, and a production monitoring design with 5-tier sampling strategy.

**Stack:** Python · Claude API (`claude-haiku-4-5` SUT, `claude-sonnet-4-6` judge) · GitHub Actions · DogStatsD · `gates.yaml`

**Key artifacts:** `eval/dataset.json` (30 cases) · `eval/prompts/judge_v1.md` (versioned judge prompt) · `.github/workflows/eval.yml` · `eval/gates.yaml` · production monitoring design

---

### [Project 05 — Enterprise Security & Compliance](./project-05-security-compliance/)
**Skill area:** LLM threat modeling · security controls · regulatory compliance · **Status:** Complete · [Doc index](./project-05-security-compliance/INDEX.md)

Produces a formal threat model for the Jira/Confluence AI assistant adapted from STRIDE to the LLM attack surface. 22 threats across all 6 STRIDE categories, 22 controls across 5 layers, two working Python implementations with 55 passing tests, and full compliance mapping to SEC Rule 17a-4(f), FINRA Rule 4511, and SOC 2 Type II — 0 gaps.

**Stack:** Python · Presidio (PII detection) · `pytest` · SOC 2 / SEC 17a-4 / FINRA 4511

**Key artifacts:** `THREAT-MODEL-001.md` (22 threats) · `GUARDRAILS-MATRIX-001.md` (22 controls) · `src/content_isolation.py` · `src/pii_scanner.py` · `COMPLIANCE-MAP-001.md`

---

### [Project 06 — Integration: Secure Agentic Pipeline](./project-06-integration-mcp-security/)
**Skill area:** Cross-project integration · security middleware composition · **Status:** Complete · [Doc index](./project-06-integration-mcp-security/INDEX.md)

Closes P05's core weakness: controls verified in isolation but never exercised in the actual pipeline. Wires P05's `content_isolation.py` and `pii_scanner.py` into P03's 3-agent pipeline as active middleware, with zero modifications to either parent project. Demonstrates that independently verified components compose correctly — and documents exactly where they don't yet (the pre-LLM hook architectural gap, deferred per ADR-002).

**Stack:** Python · `pytest` · `unittest.mock` · uv · P03 (editable dep) · P05 (sys.path injection)

**Key artifacts:** `p06/secure_researcher.py` (SecureResearcherAgent, SecureOrchestrator, PIIInFindingError) · 53/53 tests passing (injection defense, PII scan on real ResearchFinding, full pipeline regression) · `docs/integration-surface.md` (break-surface tables per wiring point) · `docs/lessons-learned.md` (4 bugs unit tests missed, P02 gateway wiring path) · SRS-001 · DESIGN-001 · ADR-001 through ADR-003

---

### [Project 07 — Sandboxed Tool Execution (gVisor)](./project-07-gvisor-sandbox/)
**Skill area:** Secure execution · container isolation · multi-tenant resource control · **Status:** Core phases complete · [Doc index](./project-07-gvisor-sandbox/INDEX.md)

Hardens Orchid's existing `ContainerRunner` task-isolation path with gVisor (`runsc`) as the runtime, real resource ceilings, default-deny network egress with explicit allowlisting, and per-execution syscall observability. Not a from-scratch sandbox, and not a new service — an integration and hardening project on top of gVisor's existing runtime and Orchid's existing isolation infrastructure.

**Stack:** `runsc` (gVisor) · Docker (alternate runtime) · Squid (egress-allowlist sidecar) · NucBox EVO X2 homelab host

**Key artifacts:** Hardened `ContainerRunner` (`--runtime`, `--memory`, `--cpus`, `--network` flags) · Squid egress-allowlist sidecar (`sandbox_egress.py`) · additive `WorkerResult` fields · syscall-interception isolation proof · per-execution syscall trace capture (`sandbox_syscall_log.py`) · live end-to-end `TesterAgent` demo under the fully hardened path · comparison write-up vs. Firecracker (P08, planned)

---

### [Project 08 — MicroVM Execution Backend with Checkpoint/Restore (Firecracker)](./project-08-firecracker-sandbox/)
**Skill area:** MicroVM isolation · durable execution · state checkpoint/recovery · **Status:** Scoped, not started · [Doc index](./project-08-firecracker-sandbox/INDEX.md)

Builds a Firecracker-backed microVM execution layer as an alternative isolation backend to P07, with pre-warmed VM pooling and snapshot/restore of a running VM's full state. Demonstrates the harder capability: resuming a long-running Orchid agent task after a simulated host failure, not just isolating it. Depends on P07's execution API contract for interchangeability between backends.

**Stack:** Firecracker · KVM · stripped Linux kernel + Alpine rootfs · NucBox EVO X2 (AMD/ROCm homelab host)

**Key artifacts (planned):** VM pool manager · snapshot/restore end-to-end demo (task killed mid-execution, resumed with correct state) · cold-start/pool-latency numbers · comparison doc vs. gVisor backend (P07)

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
| `INDEX.md` | Living artifact index with rollup checklist (root `INDEX.md` for P01, P05–P08; `docs/index.md` for P02–P04) |
| `HANDOFF.md` | Resume context — current state, gotchas, exact next action |

---

## Portfolio Review

A full written analysis of each project — individual assessment and cross-project synthesis — is in [`PORTFOLIO-REVIEW.md`](./PORTFOLIO-REVIEW.md). It includes a completion snapshot and prioritized next steps for finishing the portfolio.
