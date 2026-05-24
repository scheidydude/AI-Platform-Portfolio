from __future__ import annotations
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import GatewayConfig, TeamConfig

_bearer = HTTPBearer(auto_error=False)


def require_team(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> tuple[str, TeamConfig]:
    config: GatewayConfig = request.app.state.config
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key")
    result = config.resolve_team(token)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return result


def require_admin(request: Request) -> None:
    config: GatewayConfig = request.app.state.config
    key = request.headers.get("X-Admin-Key", "")
    if key != config.gateway.admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
