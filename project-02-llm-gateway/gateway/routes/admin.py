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
    usage_map = await store.get_all_usage_with_cost(month)
    rows = []
    for team_name, team_cfg in config.teams.items():
        row = usage_map.get(team_name, {"tokens_used": 0, "cost_usd": 0.0})
        budget = team_cfg.monthly_token_budget
        rows.append({
            "team": team_name,
            "month": month,
            "tokens_used": row["tokens_used"],
            "budget": budget,
            "pct_used": round(row["tokens_used"] / budget * 100, 1) if budget else None,
            "cost_usd": round(row["cost_usd"], 6),
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
    usage_map = await store.get_all_usage_with_cost(month)
    result = []
    for team_name, team_cfg in config.teams.items():
        row = usage_map.get(team_name, {"tokens_used": 0, "cost_usd": 0.0})
        used = row["tokens_used"]
        budget = team_cfg.monthly_token_budget
        remaining = max(0, budget - used)
        result.append({
            "team": team_name,
            "month": month,
            "tokens_used": used,
            "tokens_budget": budget,
            "tokens_remaining": remaining,
            "pct_used": round(used / budget * 100, 1) if budget else 0.0,
            "enforcement_mode": team_cfg.enforcement_mode,
            "cost_usd": round(row["cost_usd"], 6),
        })
    return {"month": month, "teams": result}


@router.get("/daily")
async def get_daily(
    request: Request,
    _: None = Depends(require_admin),
    store: QuotaStore = Depends(_get_store),
) -> dict:
    month = current_month()
    daily = await store.get_daily_usage(month)
    return {"month": month, "daily": daily}


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
