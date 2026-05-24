# ADR-001 — Framework: FastAPI

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

Need a Python HTTP framework to host the gateway. Key requirements:
- Async I/O (streaming LLM responses; don't block on long-running backend calls)
- Middleware support (auth, quota enforcement as layers)
- Easy OpenAI-compatible route definition
- Minimal overhead on the hot path

Candidates considered: Flask, FastAPI, Starlette (bare), aiohttp.

---

## Decision

**FastAPI.**

---

## Rationale

| Factor | FastAPI | Flask | Starlette (bare) |
|--------|---------|-------|-----------------|
| Native async | Yes (ASGI) | No (WSGI; asyncio possible but awkward) | Yes |
| Middleware | Starlette-native | Werkzeug; less ergonomic for async | Yes |
| OpenAPI autodoc | Built-in | Extension required | Manual |
| Request validation | Pydantic v2 built-in | Manual or extension | Manual |
| Learning curve | Low | Lowest | Medium |
| Ecosystem maturity | High | High | Medium |

FastAPI's ASGI foundation means streaming responses (`StreamingResponse`) are first-class. Auth and quota middleware compose naturally as Starlette middleware or FastAPI dependencies. Pydantic models give free request/response validation with no extra code.

Flask was ruled out because its WSGI roots make async streaming awkward and would require `asgiref` shims or Quart.

Starlette bare was ruled out — FastAPI is Starlette with ergonomics on top; no reason to use the lower layer directly.

---

## Consequences

- All async code; no sync blocking calls on hot path
- Streaming responses via `StreamingResponse` — passthrough of backend streams is clean
- Admin API gets OpenAPI docs for free at `/docs`
- Pydantic validation means bad requests fail early with structured errors

---

## Alternatives Not Chosen

- **Flask**: WSGI, streaming awkward, ruled out
- **Starlette bare**: FastAPI is strictly a superset; no benefit to going lower
- **aiohttp**: Good async HTTP server but less ergonomic for REST APIs; no DI, no OpenAPI
