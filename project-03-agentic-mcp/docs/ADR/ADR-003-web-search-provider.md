# ADR-003 — Web Search MCP Provider

**Status:** `accepted`  
**Date:** 2026-05-23  
**Author:** David Scheiderman

---

## Context

The Researcher agent needs a web search MCP. Original candidates were Brave Search and Tavily. User operates a self-hosted SearXNG instance at `https://search.scheidy.com/`. Choice affects API key cost, result quality, privacy, and whether a custom MCP server must be authored.

---

## Decision

**Self-hosted SearXNG at `https://search.scheidy.com/`.** No external API key dependency. Requires authoring a custom MCP server wrapper around the SearXNG JSON API.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| SearXNG (self-hosted, `https://search.scheidy.com/`) | No API cost, no rate limit surprises, privacy-preserving, full control, already running | Must author custom MCP server; no pre-built package |
| Brave Search | Free tier, existing MCP server packages | External API dependency, rate limits hit during Phase 5 experiments |
| Tavily | AI-agent-optimized structured results | Paid after free tier; external dependency |

---

## Rationale

SearXNG eliminates all external API cost and rate limit risk. Since Phase 5 experiments deliberately exhaust tool budgets and inject failures, having a self-hosted endpoint avoids accidental cost overruns and gives full control over simulated failure conditions. The cost is authoring a thin MCP server around SearXNG's JSON API — an acceptable addition that itself produces a reusable artifact.

SearXNG JSON API endpoint: `https://search.scheidy.com/search?q=<query>&format=json`

---

## Consequences

**Positive:**
- Zero external API cost — unlimited calls during Phase 5 experiments
- Full control over the search backend (can inject failures, inspect logs)
- Custom MCP server is a reusable portfolio artifact
- No rate limit surprises

**Negative / trade-offs:**
- Must author a custom MCP server for SearXNG (adds ~0.5 day to Phase 2)
- Results quality depends on SearXNG engine configuration
- No `fetch_page` built in — must implement separately or use `httpx` directly

**Risks:**
- If `https://search.scheidy.com/` is unavailable, pipeline has no web search fallback — acceptable for homelab PoC

---

## Related ADRs

- ADR-002: MCP client library

---

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-05-23 | `proposed` | Brave and Tavily considered |
| 2026-05-23 | `accepted` | Self-hosted SearXNG chosen; custom MCP server required |
