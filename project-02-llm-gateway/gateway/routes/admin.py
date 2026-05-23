from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from ..middleware.auth import require_admin
from ..observability import current_month
from ..state.base import QuotaStore

router = APIRouter(prefix="/admin")


def _get_store(request: Request) -> QuotaStore:
    return request.app.state.store


@router.get("/usage")
async def get_usage(
    request: Request,
    _: None = Depends(require_admin),
    store: QuotaStore = Depends(_get_store),
) -> dict:
    month = current_month()
    config = request.app.state.config
    usage = await store.get_all_usage(month)
    # Annotate with budget info
    rows = []
    for row in usage:
        team_cfg = config.teams.get(row["team"])
        budget = team_cfg.monthly_token_budget if team_cfg else 0
        rows.append({
            **row,
            "month": month,
            "budget": budget,
            "pct_used": round(row["tokens_used"] / budget * 100, 1) if budget else None,
        })
    return {"month": month, "teams": rows}


@router.get("/quota")
async def get_quota(
    request: Request,
    _: None = Depends(require_admin),
    store: QuotaStore = Depends(_get_store),
) -> dict:
    month = current_month()
    config = request.app.state.config
    result = []
    for team_name, team_cfg in config.teams.items():
        used = await store.get_usage(team_name, month)
        remaining = max(0, team_cfg.monthly_token_budget - used)
        result.append({
            "team": team_name,
            "month": month,
            "tokens_used": used,
            "tokens_budget": team_cfg.monthly_token_budget,
            "tokens_remaining": remaining,
            "pct_used": round(used / team_cfg.monthly_token_budget * 100, 1),
            "enforcement_mode": team_cfg.enforcement_mode,
        })
    return {"month": month, "teams": result}


@router.post("/reset")
async def reset_quota(
    request: Request,
    _: None = Depends(require_admin),
    store: QuotaStore = Depends(_get_store),
) -> dict:
    body = await request.json()
    team_name = body.get("team")
    month = body.get("month", current_month())

    config = request.app.state.config
    if team_name not in config.teams:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    await store.reset(team_name, month)
    return {"ok": True, "team": team_name, "month": month}
