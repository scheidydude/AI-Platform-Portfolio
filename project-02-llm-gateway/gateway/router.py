from __future__ import annotations
from dataclasses import dataclass

from .config import GatewayConfig, TeamConfig
from .observability import logger


@dataclass
class RoutingDecision:
    primary: str          # backend name to send the real request
    strategy: str         # which strategy produced this decision
    shadow: str | None = None  # backend name for shadow copy (shadow strategy only)


class Router:
    """Stateless router — all four strategies implemented here."""

    def select(
        self,
        team_name: str,
        team_cfg: TeamConfig,
        requested_model: str,
        config: GatewayConfig,
    ) -> RoutingDecision:
        s = team_cfg.routing_strategy
        if s == "static":
            return self._static(team_name, team_cfg, requested_model, config)
        if s == "cost_aware":
            return self._cost_aware(team_name, team_cfg, config)
        if s == "fallback":
            return self._fallback(team_name, team_cfg, requested_model, config)
        if s == "shadow":
            return self._shadow(team_name, team_cfg, requested_model, config)
        logger.warning({"event": "unknown_routing_strategy", "strategy": s, "team": team_name})
        return self._static(team_name, team_cfg, requested_model, config)

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _static(
        self, team_name: str, team_cfg: TeamConfig, requested_model: str, config: GatewayConfig
    ) -> RoutingDecision:
        name = self._resolve(team_cfg, requested_model, config)
        if name is None:
            raise ValueError(f"No backend configured for team '{team_name}'")
        return RoutingDecision(primary=name, strategy="static")

    def _cost_aware(
        self, team_name: str, team_cfg: TeamConfig, config: GatewayConfig
    ) -> RoutingDecision:
        best_name: str | None = None
        best_cost = float("inf")
        for name in team_cfg.models_allowed:
            bc = config.backends.get(name)
            if bc is None:
                continue
            cost = bc.cost_per_1k_prompt + bc.cost_per_1k_completion
            if cost < best_cost:
                best_cost = cost
                best_name = name
        if best_name is None:
            raise ValueError(f"No eligible backends for cost_aware routing for team '{team_name}'")
        logger.info({
            "event": "cost_aware_routing",
            "team": team_name,
            "selected": best_name,
            "combined_cost_per_2k": best_cost,
        })
        return RoutingDecision(primary=best_name, strategy="cost_aware")

    def _fallback(
        self, team_name: str, team_cfg: TeamConfig, requested_model: str, config: GatewayConfig
    ) -> RoutingDecision:
        name = self._resolve(team_cfg, requested_model, config)
        if name is None:
            raise ValueError(f"No primary backend for fallback routing for team '{team_name}'")
        # fallback_backend validated at request time when primary fails
        return RoutingDecision(primary=name, strategy="fallback")

    def _shadow(
        self, team_name: str, team_cfg: TeamConfig, requested_model: str, config: GatewayConfig
    ) -> RoutingDecision:
        name = self._resolve(team_cfg, requested_model, config)
        if name is None:
            raise ValueError(f"No primary backend for shadow routing for team '{team_name}'")
        shadow = (
            team_cfg.shadow_backend
            if team_cfg.shadow_backend and team_cfg.shadow_backend in config.backends
            else None
        )
        if shadow is None:
            logger.warning({"event": "shadow_backend_missing", "team": team_name})
        return RoutingDecision(primary=name, strategy="shadow", shadow=shadow)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve(
        self, team_cfg: TeamConfig, requested_model: str, config: GatewayConfig
    ) -> str | None:
        sel = config.select_backend(team_cfg, requested_model)
        return sel[0] if sel else None
