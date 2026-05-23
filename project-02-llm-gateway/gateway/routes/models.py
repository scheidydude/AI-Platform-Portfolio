from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from ..config import GatewayConfig, TeamConfig
from ..middleware.auth import require_team

router = APIRouter()


@router.get("/v1/models")
async def list_models(
    request: Request,
    auth: tuple[str, TeamConfig] = Depends(require_team),
) -> dict:
    config: GatewayConfig = request.app.state.config
    _, team = auth
    return {
        "object": "list",
        "data": [
            {"id": m, "object": "model", "owned_by": "gateway"}
            for m in team.models_allowed
            if m in config.backends
        ],
    }
