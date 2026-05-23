# ADR-001 — Language and Framework Selection

**Status:** `accepted`  
**Date:** 2026-05-23  
**Author:** David Scheiderman

---

## Context

Need to pick language and base framework for the 3-agent pipeline. Decision gates all Phase 2–4 work. Must be compatible with available MCP SDKs and support async I/O (multiple researcher tasks may run concurrently).

---

## Decision

**Python.** No framework abstraction layer — plain Python with Pydantic for schema validation and the `mcp` SDK for tool integration.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Python + `mcp` SDK | Best MCP SDK support, Pydantic native, strong AI ecosystem, largest homelab tooling surface | GIL limits true parallelism (asyncio works around it for I/O-bound tool calls) |
| TypeScript + `@anthropic-ai/sdk` | Truly async, strong typing | Less AI tooling, no Pydantic equivalent |
| Python + LangChain/LangGraph | Pre-built agent abstractions | Abstraction hides failure modes — defeats project purpose |

---

## Rationale

Python chosen for ecosystem fit: `mcp` SDK is Python-first, Pydantic is native, and the AI tooling surface (inspection, debugging, logging) is richer. The GIL is not a blocker — researcher tool calls are I/O-bound and asyncio handles concurrency adequately. LangChain/LangGraph explicitly rejected because this project's goal is to surface failure modes — an abstraction layer would hide exactly what we want to see.

---

## Consequences

**Positive:**
- Pydantic used for all handoff schemas — types enforced at runtime
- Rich ecosystem for MCP, HTTP clients, JSON serialization
- Homelab tooling (SearXNG, GitHub) has Python client support

**Negative / trade-offs:**
- No true thread-level parallelism for CPU-bound work (not relevant here)
- More verbose error handling than TypeScript for async flows

**Risks:**
- None significant for this scope

---

## Related ADRs

- ADR-002: MCP client library selection
- ADR-005: Orchestration pattern

---

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-05-23 | `proposed` | Options framed, decision pending |
| 2026-05-23 | `accepted` | Python chosen |
