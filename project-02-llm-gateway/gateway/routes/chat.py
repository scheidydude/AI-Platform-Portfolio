from __future__ import annotations
import json
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..backends import LLMBackend
from ..config import GatewayConfig, TeamConfig
from ..middleware.auth import require_team
from ..models import ChatCompletionRequest, ChatCompletionResponse, ChatChoice, Message, UsageInfo
from ..observability import current_month, generate_request_id, log_request, logger
from ..quota import EnforcementAction, check_quota
from ..ratelimit import RateLimiter
from ..state.base import QuotaStore
from ..tokens import estimate_tokens

router = APIRouter()


def _get_store(request: Request) -> QuotaStore:
    return request.app.state.store


def _get_backends(request: Request) -> dict[str, LLMBackend]:
    return request.app.state.backends


def _get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    auth: tuple[str, TeamConfig] = Depends(require_team),
    store: QuotaStore = Depends(_get_store),
    backends: dict[str, LLMBackend] = Depends(_get_backends),
    rate_limiter: RateLimiter = Depends(_get_rate_limiter),
):
    config: GatewayConfig = request.app.state.config
    team_name, team_cfg = auth
    request_id = generate_request_id()
    start_time = time.monotonic()
    month = current_month()

    # --- Rate limit check (in-memory, no I/O) ---
    if not rate_limiter.check_and_record(team_name, team_cfg.rate_limit_rpm):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "team": team_name,
                "limit_rpm": team_cfg.rate_limit_rpm,
            },
        )

    estimated = estimate_tokens([m.model_dump() for m in body.messages])

    # --- Quota enforcement ---
    decision = await check_quota(team_name, team_cfg, store)

    if decision.action == EnforcementAction.BLOCK:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "team": team_name,
                "tokens_used": decision.tokens_used,
                "tokens_budget": decision.tokens_budget,
            },
        )

    # --- Backend selection (may be overridden by downgrade) ---
    if decision.action == EnforcementAction.DOWNGRADE and decision.backend_override:
        backend_name = decision.backend_override
        if backend_name not in backends:
            # Downgrade target not available — fall through to normal selection
            logger.warning({
                "event": "downgrade_backend_missing",
                "team": team_name,
                "backend": backend_name,
            })
            backend_name = _resolve_backend(config, team_cfg, body.model)
    else:
        backend_name = _resolve_backend(config, team_cfg, body.model)

    if backend_name is None or backend_name not in backends:
        raise HTTPException(status_code=502, detail="No backend configured for team")
    backend = backends[backend_name]

    enforcement_action = decision.action.value

    async def _account(prompt_tokens: int, completion_tokens: int, status: str) -> None:
        total = prompt_tokens + completion_tokens
        new_used = await store.increment(team_name, month, total)
        await store.log_request(
            request_id=request_id,
            team=team_name,
            model=body.model,
            backend=backend_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_tokens=estimated,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            status=status,
        )
        log_request(
            request_id=request_id,
            team=team_name,
            model=body.model,
            backend=backend_name,
            routing_strategy=team_cfg.routing_strategy,
            enforcement_action=enforcement_action,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_tokens=estimated,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            status=status,
            quota_used=new_used,
            quota_budget=team_cfg.monthly_token_budget,
        )

    # --- Streaming path ---
    if body.stream:
        usage: dict = {}

        async def generate():
            try:
                async for chunk in backend.stream(body):
                    decoded = chunk.decode("utf-8", errors="replace").rstrip("\n")
                    if decoded.startswith("data: ") and "[DONE]" not in decoded:
                        try:
                            data = json.loads(decoded[6:])
                            if data.get("usage"):
                                usage.update(data["usage"])
                        except (json.JSONDecodeError, KeyError):
                            pass
                    yield chunk
                    if not chunk.endswith(b"\n\n"):
                        yield b"\n"
            except httpx.HTTPStatusError as exc:
                logger.error({"event": "stream_error", "request_id": request_id, "status": exc.response.status_code})
            except httpx.RequestError as exc:
                logger.error({"event": "stream_error", "request_id": request_id, "error": str(exc)})
            finally:
                pt = usage.get("prompt_tokens", estimated)
                ct = usage.get("completion_tokens", 0)
                await _account(pt, ct, "success")

        return StreamingResponse(generate(), media_type="text/event-stream")

    # --- Non-streaming path ---
    try:
        result = await backend.complete(body)
    except httpx.HTTPStatusError as exc:
        await _account(estimated, 0, "error")
        raise HTTPException(status_code=502, detail=f"Backend HTTP {exc.response.status_code}")
    except httpx.RequestError as exc:
        await _account(estimated, 0, "error")
        raise HTTPException(status_code=502, detail=f"Backend unreachable: {exc}")

    await _account(result.prompt_tokens, result.completion_tokens, "success")

    return ChatCompletionResponse(
        id=request_id,
        model=body.model,
        choices=[ChatChoice(message=Message(role="assistant", content=result.content))],
        usage=UsageInfo(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.prompt_tokens + result.completion_tokens,
        ),
    )


def _resolve_backend(
    config: GatewayConfig, team_cfg: TeamConfig, requested_model: str
) -> str | None:
    selection = config.select_backend(team_cfg, requested_model)
    return selection[0] if selection else None
