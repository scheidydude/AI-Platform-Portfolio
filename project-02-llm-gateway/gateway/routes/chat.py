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
from ..state.base import QuotaStore
from ..tokens import estimate_tokens

router = APIRouter()


def _get_store(request: Request) -> QuotaStore:
    return request.app.state.store


def _get_backends(request: Request) -> dict[str, LLMBackend]:
    return request.app.state.backends


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    auth: tuple[str, TeamConfig] = Depends(require_team),
    store: QuotaStore = Depends(_get_store),
    backends: dict[str, LLMBackend] = Depends(_get_backends),
):
    config: GatewayConfig = request.app.state.config
    team_name, team_cfg = auth
    request_id = generate_request_id()
    start_time = time.monotonic()
    month = current_month()

    estimated = estimate_tokens([m.model_dump() for m in body.messages])

    selection = config.select_backend(team_cfg, body.model)
    if selection is None:
        raise HTTPException(status_code=502, detail="No backend configured for team")
    backend_name, _ = selection
    backend = backends.get(backend_name)
    if backend is None:
        raise HTTPException(status_code=502, detail=f"Backend '{backend_name}' not initialized")

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
        quota_remaining = max(0, team_cfg.monthly_token_budget - new_used)
        log_request(
            request_id=request_id,
            team=team_name,
            model=body.model,
            backend=backend_name,
            routing_strategy=team_cfg.routing_strategy,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_tokens=estimated,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            status=status,
            quota_remaining=quota_remaining,
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
                    # SSE event separator after each line
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
