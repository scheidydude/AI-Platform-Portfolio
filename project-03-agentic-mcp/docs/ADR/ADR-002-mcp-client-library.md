# ADR-002 — MCP Client Library Selection

**Status:** `accepted`  
**Date:** 2026-05-23  
**Author:** David Scheiderman

---

## Context

Need to select how to connect to MCP servers. Options range from using the official MCP Python SDK directly, to using Anthropic's SDK tool-use layer, to using a higher-level framework. This decision affects how tool calls are made, how errors are surfaced, and how much control we have over the raw protocol.

---

## Decision

**`mcp` Python SDK (official).** Connect to MCP servers directly via the protocol SDK, not through an abstraction layer.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| `mcp` Python SDK (official) | Direct protocol access, explicit control, raw error surfaces visible, teaches the actual protocol | More boilerplate, lower-level |
| Anthropic SDK tool_use | Native integration with Claude model calls, clean DX | Tool definitions managed manually, less MCP-specific |
| `langchain-mcp` / similar | Abstraction handles protocol details | Hides failure modes — defeats learning purpose |

---

## Rationale

The `mcp` SDK is chosen because raw protocol access is the point. This project is explicitly designed to surface tool failure modes — using an abstraction that sanitizes errors would undermine Phase 2–3 learning objectives. The added boilerplate is a feature: it forces explicit handling of every error class in the `ToolResult` wrapper.

---

## Consequences

**Positive:**
- Every tool call error is visible and must be handled explicitly
- Builds transferable knowledge of the MCP protocol itself
- Compatible with both SearXNG (custom MCP server) and GitHub MCP server

**Negative / trade-offs:**
- More boilerplate per tool integration than Anthropic SDK tool_use
- May need to write a thin MCP server wrapper for SearXNG if no existing server exists

**Risks:**
- SearXNG MCP server may not exist as a pre-built package — may need to author one (adds Phase 2 scope)

---

## Related ADRs

- ADR-001: Language and framework
- ADR-003: Web search provider

---

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-05-23 | `proposed` | Options framed, decision pending |
| 2026-05-23 | `accepted` | `mcp` Python SDK chosen |
