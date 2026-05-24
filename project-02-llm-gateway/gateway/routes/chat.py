from __future__ import annotations
import asyncio
import json
import time
from typing import TYPE_CHECKING

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .. import metrics as gw_metrics
from ..backends import LLMBackend
from ..config import BackendConfig, GatewayConfig, TeamConfig
from ..middleware.auth import require_team
from ..models import ChatCompletionRequest, ChatCompletionResponse, ChatChoice, Message, UsageInfo
from ..observability import current_month, generate_request_id, log_request, logger
from ..quota import EnforcementAction, check_quota
from ..ratelimit import RateLimiter
from ..router import Router, RoutingDecision
from ..state.base import QuotaStore
from ..tokens import estimate_tokens

router = APIRouter()

# Keep shadow task references to prevent premature GC
_shadow_tasks: set[asyncio.Task] = set()


def _get_store(request: Request) -> QuotaStore:
    return request.app.state.store


def _get_backends(request: Request) -> dict[str, LLMBackend]:
    return request.app.state.backends


def _get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def _get_router(request: Request) -> Router:
    return request.app.state.router


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    auth: tuple[str, TeamConfig] = Depends(require_team),
    store: QuotaStore = Depends(_get_store),
    backends: dict[str, LLMBackend] = Depends(_get_backends),
    rate_limiter: RateLimiter = Depends(_get_rate_limiter),
    gw_router: Router = Depends(_get_router),
):
    config: GatewayConfig = request.app.state.config
    team_name, team_cfg = auth
    request_id = generate_request_id()
    start_time = time.monotonic()
    month = current_month()

    # --- Rate limit ---
    if not rate_limiter.check_and_record(team_name, team_cfg.rate_limit_rpm):
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limited", "team": team_name, "limit_rpm": team_cfg.rate_limit_rpm},
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

    # --- Routing (downgrade overrides router) ---
    if decision.action == EnforcementAction.DOWNGRADE and decision.backend_override:
        if decision.backend_override in backends:
            routing = RoutingDecision(primary=decision.backend_override, strategy="downgrade")
        else:
            logger.warning({"event": "downgrade_backend_missing", "team": team_name, "backend": decision.backend_override})
            routing = _route(gw_router, team_name, team_cfg, body.model, config)
    else:
        routing = _route(gw_router, team_name, team_cfg, body.model, config)

    if routing is None or routing.primary not in backends:
        raise HTTPException(status_code=502, detail="No backend available for team")

    enforcement_action = decision.action.value

    # --- Accounting closure (backend may change due to fallback) ---
    async def _account(
        pt: int,
        ct: int,
        status: str,
        used_backend_name: str,
        used_backend_cfg: BackendConfig,
    ) -> None:
        cost_usd = (
            pt * used_backend_cfg.cost_per_1k_prompt / 1000
            + ct * used_backend_cfg.cost_per_1k_completion / 1000
        )
        latency_ms = int((time.monotonic() - start_time) * 1000)
        new_used = await store.increment(team_name, month, pt + ct)
        await store.log_request(
            request_id=request_id,
            team=team_name,
            model=body.model,
            backend=used_backend_name,
            prompt_tokens=pt,
            completion_tokens=ct,
            estimated_tokens=estimated,
            latency_ms=latency_ms,
            status=status,
            cost_usd=cost_usd,
        )
        log_request(
            request_id=request_id,
            team=team_name,
            model=body.model,
            backend=used_backend_name,
            routing_strategy=routing.strategy,
            enforcement_action=enforcement_action,
            prompt_tokens=pt,
            completion_tokens=ct,
            estimated_tokens=estimated,
            latency_ms=latency_ms,
            status=status,
            cost_usd=cost_usd,
            quota_used=new_used,
            quota_budget=team_cfg.monthly_token_budget,
        )
        gw_metrics.record(
            team=team_name,
            model=body.model,
            backend=used_backend_name,
            status=status,
            enforcement_action=enforcement_action,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_seconds=latency_ms / 1000,
            cost_usd=cost_usd,
            quota_used=new_used,
            quota_budget=team_cfg.monthly_token_budget,
        )

    backend_name = routing.primary
    backend = backends[backend_name]
    backend_cfg = config.backends[backend_name]

    # --- Shadow: fire-and-forget (non-streaming, no quota impact) ---
    if routing.shadow and routing.shadow in backends:
        task = asyncio.create_task(
            _run_shadow(backends[routing.shadow], body, request_id, backend_name, routing.shadow)
        )
        _shadow_tasks.add(task)
        task.add_done_callback(_shadow_tasks.discard)

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
                await _account(pt, ct, "success", backend_name, backend_cfg)

        return StreamingResponse(generate(), media_type="text/event-stream")

    # --- Non-streaming path (supports fallback) ---
    try:
        result = await backend.complete(body)
        await _account(result.prompt_tokens, result.completion_tokens, "success", backend_name, backend_cfg)
    except (httpx.HTTPStatusError, httpx.RequestError) as primary_exc:
        fb_name = team_cfg.fallback_backend
        if routing.strategy == "fallback" and fb_name and fb_name in backends:
            logger.info({
                "event": "fallback_triggered",
                "request_id": request_id,
                "team": team_name,
                "from": backend_name,
                "to": fb_name,
                "reason": str(primary_exc),
            })
            fb_backend = backends[fb_name]
            fb_cfg = config.backends[fb_name]
            try:
                result = await fb_backend.complete(body)
                await _account(result.prompt_tokens, result.completion_tokens, "success", fb_name, fb_cfg)
                backend_name = fb_name  # update for response metadata
            except (httpx.HTTPStatusError, httpx.RequestError) as fb_exc:
                await _account(estimated, 0, "error", fb_name, fb_cfg)
                raise HTTPException(
                    status_code=502,
                    detail=f"Both backends failed — primary: {primary_exc}; fallback: {fb_exc}",
                )
        else:
            await _account(estimated, 0, "error", backend_name, backend_cfg)
            raise HTTPException(status_code=502, detail=f"Backend error: {primary_exc}")

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


def _route(
    gw_router: Router,
    team_name: str,
    team_cfg: TeamConfig,
    requested_model: str,
    config: GatewayConfig,
) -> RoutingDecision | None:
    try:
        return gw_router.select(team_name, team_cfg, requested_model, config)
    except ValueError as e:
        logger.error({"event": "routing_error", "team": team_name, "error": str(e)})
        return None


async def _run_shadow(
    shadow_backend: LLMBackend,
    body: ChatCompletionRequest,
    primary_request_id: str,
    primary_backend_name: str,
    shadow_backend_name: str,
) -> None:
    try:
        result = await shadow_backend.complete(body)
        logger.info({
            "event": "shadow_comparison",
            "primary_request_id": primary_request_id,
            "primary_backend": primary_backend_name,
            "shadow_backend": shadow_backend_name,
            "shadow_prompt_tokens": result.prompt_tokens,
            "shadow_completion_tokens": result.completion_tokens,
            "shadow_content_length": len(result.content),
        })
    except Exception as exc:
        logger.warning({
            "event": "shadow_error",
            "primary_request_id": primary_request_id,
            "shadow_backend": shadow_backend_name,
            "error": str(exc),
        })
