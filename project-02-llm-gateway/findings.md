# Findings — LLM Gateway

Research and discoveries as they accumulate.

---

## Stack Decisions

### FastAPI
- Native async → clean streaming passthrough
- OpenAPI autodoc → useful for admin API
- Starlette middleware → auth + quota checks as middleware layers

### Token Counting
- `tiktoken` for OpenAI models (cl100k_base for GPT-4/Claude-compatible)
- Bedrock uses its own token counting — check `anthropic_tokens` in response headers
- Pre-request estimate via tiktoken, post-request reconcile with actual from response

### State Store
- SQLite (phase 1): good for single-node, simple quota tracking
- Redis (phase 2+): atomic INCR for quota enforcement under concurrent load — critical to avoid race conditions when multiple requests hit quota boundary simultaneously

### Backend Auth
- Bedrock: boto3 with IAM role / AWS credentials
- OpenAI-compat: `Authorization: Bearer <key>` header passthrough
- llama.cpp: typically unauthenticated local HTTP

---

## Key Risks

1. **Token counting accuracy**: tiktoken estimate vs. actual diverges for non-OpenAI models. Log both and reconcile.
2. **Streaming quota accounting**: can't know final token count until stream ends — enforce based on estimate, adjust post-stream.
3. **Concurrent quota exhaustion**: two requests both pass quota check at 4,999,900 tokens, both send. Redis INCR + check is atomic; SQLite is not.

---

## Reference Links

- tiktoken: https://github.com/openai/tiktoken
- FastAPI streaming: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
- Bedrock API: AWS docs `bedrock-runtime` InvokeModelWithResponseStream
- LiteLLM source (reference): https://github.com/BerriAI/litellm

---

## Bifrost / LiteLLM Research

_To be filled during Phase 5 comparison work._

| Feature | Notes |
|---------|-------|
| Bifrost quota | |
| LiteLLM quota | |
| Bifrost routing | |
| LiteLLM routing | |
