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

Completed in Phase 5. Full analysis in [DESIGN-002](docs/design/DESIGN-002-vendor-comparison.md).

| Feature | Bifrost | LiteLLM |
|---------|---------|---------|
| Quota enforcement | Basic RPM/TPM rate limiting; no budget governance model | Full budget management — per-team/user/model; Redis-backed atomic ops; monthly/daily reset; carry-over; battle-tested streaming edge cases |
| Routing strategies | Static, round-robin, fallback | Static, fallback, round-robin, lowest-latency (stateful p50/p99), lowest-cost, usage-based; `num_retries` + `timeout` per deployment |
| Shadow routing | Not supported | Not supported (gap — only our build has this) |
| Observability | Prometheus + structured logs; no callback ecosystem | Prometheus + 20+ callback integrations (Langfuse, Datadog, Helicone, S3, Sentry, custom webhook) |
| Operational overhead | Single Go binary; ~20MB RAM; <200ms cold start; Redis optional | Python; Redis required in prod; Postgres for logging; 200-400MB RAM; Docker Compose recommended |
| Enterprise auth | API key; limited enterprise options | Enterprise: SSO (Okta/Azure AD/Google), OIDC/SAML, RBAC, team management UI |
| Audit logging | Structured logs to stdout; operator-configured shipping | Postgres persistence; S3 callback; Enterprise audit metadata |
| Key insight | Right choice at >5000 RPS where Python interpreter overhead is measurable | Right choice for teams needing cost governance, SSO, or observability integrations without building them |
