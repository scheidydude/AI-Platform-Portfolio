from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .config import TeamConfig
from .observability import current_month, logger
from .state.base import QuotaStore


class EnforcementAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"        # hard mode, quota exhausted → 429
    WARN = "warn"          # soft mode, quota exhausted → allow + log warning
    DOWNGRADE = "downgrade"  # downgrade mode, near/over threshold → cheap backend


@dataclass
class QuotaDecision:
    action: EnforcementAction
    tokens_used: int
    tokens_budget: int
    backend_override: str | None = None  # set when action == DOWNGRADE


async def check_quota(
    team_name: str,
    team_cfg: TeamConfig,
    store: QuotaStore,
) -> QuotaDecision:
    month = current_month()
    used = await store.get_usage(team_name, month)
    budget = team_cfg.monthly_token_budget
    mode = team_cfg.enforcement_mode

    if mode == "hard":
        if used >= budget:
            return QuotaDecision(EnforcementAction.BLOCK, used, budget)
        return QuotaDecision(EnforcementAction.ALLOW, used, budget)

    if mode == "soft":
        if used >= budget:
            logger.warning({
                "event": "quota_exceeded",
                "team": team_name,
                "tokens_used": used,
                "tokens_budget": budget,
                "enforcement": "soft_cap",
                "action": "allow_with_warning",
            })
            return QuotaDecision(EnforcementAction.WARN, used, budget)
        return QuotaDecision(EnforcementAction.ALLOW, used, budget)

    if mode == "downgrade":
        threshold = int(budget * team_cfg.downgrade_threshold_pct / 100)
        if used >= threshold and team_cfg.downgrade_to:
            logger.warning({
                "event": "quota_threshold_reached",
                "team": team_name,
                "tokens_used": used,
                "tokens_budget": budget,
                "threshold_pct": team_cfg.downgrade_threshold_pct,
                "downgrade_to": team_cfg.downgrade_to,
            })
            return QuotaDecision(
                EnforcementAction.DOWNGRADE,
                used,
                budget,
                backend_override=team_cfg.downgrade_to,
            )
        return QuotaDecision(EnforcementAction.ALLOW, used, budget)

    # Unknown mode — fail open, log so it's visible
    logger.warning({"event": "unknown_enforcement_mode", "team": team_name, "mode": mode})
    return QuotaDecision(EnforcementAction.ALLOW, used, budget)
