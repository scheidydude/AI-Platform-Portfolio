# ADR-006 — LLM Backend

**Status:** `accepted`  
**Date:** 2026-05-23  
**Author:** David Scheiderman

---

## Context

The Researcher agent needs a language model for reasoning and tool-use orchestration. Initial design assumed Anthropic Claude API. During Phase 2 implementation, user identified a self-hosted llama.cpp server already running on homelab. Decision affects API key requirements, cost, model capability, and SDK choice.

---

## Decision

**Self-hosted llama.cpp at `http://ai.scheidy.com:8082` running Qwen3-35B-A3B (MXFP4 MoE quantization).** OpenAI-compatible API. No external API key required.

---

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| Anthropic Claude API | Strongest tool-use, reliable, Anthropic SDK | External cost, API key required, rate limits |
| Self-hosted Qwen3-35B via llama.cpp | No cost, no key, full control, homelab, Qwen3 supports tool calling | Inference speed limited by hardware, no SLA |
| OpenAI API | Reliable tool-use, large ecosystem | External cost, API key required |

---

## Rationale

Self-hosted is zero marginal cost for a learning project, already running, and Qwen3-35B (MoE) has capable tool calling support. Using the OpenAI-compatible API means the `openai` Python SDK works directly — no custom HTTP client needed. The `/no_think` prefix in the system prompt disables Qwen3's extended reasoning mode for faster, more direct responses.

---

## Technical details

- **Endpoint:** `http://ai.scheidy.com:8082/v1/chat/completions`
- **Model ID:** `Qwen3.6-35B-A3B-MXFP4_MOE.gguf`
- **SDK:** `openai` Python SDK (`AsyncOpenAI` with custom `base_url`)
- **Tool calling format:** OpenAI function-calling (`type: "function"`)
- **Thinking mode:** Disabled via `/no_think` in system prompt

---

## Consequences

**Positive:**
- Zero API cost — unlimited calls during Phase 5 experiments
- Full control over inference (can adjust context, temperature, etc.)
- OpenAI SDK is widely documented

**Negative / trade-offs:**
- Replaced `anthropic` SDK with `openai` SDK — tool definition format changed from `input_schema` to `parameters`
- Tool result format changed from Anthropic `tool_result` blocks to OpenAI `role: "tool"` messages
- Model response quality/speed depends on homelab hardware
- No fallback if `http://ai.scheidy.com:8082` is down

**Risks:**
- If model doesn't call tools correctly, need to debug prompt engineering rather than SDK config

---

## Related ADRs

- ADR-001: Language (Python)
- ADR-002: MCP client library
- ADR-003: SearXNG web search

---

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-05-23 | `proposed` | Anthropic API assumed in initial design |
| 2026-05-23 | `accepted` | Switched to self-hosted Qwen3 on llama.cpp; validated end-to-end |
