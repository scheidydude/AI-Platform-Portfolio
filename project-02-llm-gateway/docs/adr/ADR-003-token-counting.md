# ADR-003 — Token Counting: tiktoken + Post-Request Reconciliation

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

Quota enforcement needs token counts. Two points in the lifecycle where counts are available:

1. **Pre-request**: estimate from message content before sending (needed for pre-flight budget check)
2. **Post-request**: actual counts from backend response headers (authoritative, but too late for pre-flight)

These two numbers will not always match. The strategy for handling the gap is a design decision.

---

## Decision

**Use tiktoken for pre-request estimation. Reconcile with actual counts post-request. Log both. Debit quota using actual.**

---

## Rationale

### Pre-request: tiktoken

- OpenAI's official tokenizer; `cl100k_base` encoding matches Claude and GPT-4 token counts closely (within ~5% for typical prompts)
- Fast: tokenization is CPU-bound and completes in microseconds
- Enables fail-fast: reject requests that would clearly exceed budget before any backend call

### Post-request: actual counts from response

- Bedrock returns `anthropic-usage` header with `input_tokens` / `output_tokens`
- OpenAI-compat backends return usage object in response body
- llama.cpp returns usage in response JSON

Actual counts are authoritative. Quota debit always uses actual, not estimate.

### Reconciliation

Log `estimated_tokens` alongside `actual_tokens` on every request. Track discrepancy over time. If estimate consistently undershoots by >20%, adjust estimation strategy or add a safety buffer multiplier.

### The gap problem for streaming

With streaming responses, the full token count isn't known until the stream ends. Strategy:

1. Pre-flight check uses estimated tokens
2. During stream passthrough, accumulate response chunks
3. Post-stream: read actual from response termination metadata
4. Debit quota from actual count

This means a request could start and stream partway through before the final quota debit is known. Acceptable for POC; production would require reservation-based accounting (reserve estimated at start, release delta at end).

---

## Consequences

- Must log `estimated_tokens` and `actual_tokens` on every request
- Quota debit happens post-stream, not pre-request — slight overage possible at quota boundary
- Discrepancy metric enables tuning tiktoken encoding choice over time
- llama.cpp token counts may require separate counting strategy if it uses a different tokenizer (e.g., SentencePiece for Llama models)

---

## Open Issues

- Llama models use SentencePiece, not BPE. tiktoken `cl100k_base` will be inaccurate for llama.cpp backend. May need `llama-cpp-python` tokenizer or a buffer multiplier. Track in findings.md.

---

## Alternatives Not Chosen

- **Character-based approximation** (4 chars ≈ 1 token): too inaccurate; 30%+ error rate on code-heavy prompts
- **Count only actual, skip pre-flight**: can't fail-fast before making expensive backend call
- **Count only estimate, never reconcile**: quota drift over time; correctness degrades
