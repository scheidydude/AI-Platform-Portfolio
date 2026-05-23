from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, Field
import yaml


class BackendConfig(BaseModel):
    type: str
    base_url: str = ""
    api_key: str = ""
    model_id: str = ""
    cost_per_1k_prompt: float = 0.0
    cost_per_1k_completion: float = 0.0


class TeamConfig(BaseModel):
    api_key: str
    monthly_token_budget: int
    models_allowed: list[str] = Field(default_factory=list)
    rate_limit_rpm: int = 60
    enforcement_mode: str = "hard"       # hard | soft | downgrade
    downgrade_threshold_pct: int = 80
    downgrade_to: str = ""
    routing_strategy: str = "static"
    default_backend: str = ""


class GatewaySettings(BaseModel):
    admin_key: str
    metrics_backend: str = "stdout"


class GatewayConfig(BaseModel):
    gateway: GatewaySettings
    teams: dict[str, TeamConfig] = Field(default_factory=dict)
    backends: dict[str, BackendConfig] = Field(default_factory=dict)

    def resolve_team(self, api_key: str) -> tuple[str, TeamConfig] | None:
        for name, team in self.teams.items():
            if team.api_key == api_key:
                return name, team
        return None

    def select_backend(
        self, team: TeamConfig, requested_model: str
    ) -> tuple[str, BackendConfig] | None:
        # Client-requested model matches a configured backend and is allowed
        if requested_model in team.models_allowed and requested_model in self.backends:
            return requested_model, self.backends[requested_model]
        # Explicit default
        if team.default_backend and team.default_backend in self.backends:
            return team.default_backend, self.backends[team.default_backend]
        # First allowed backend that exists
        for name in team.models_allowed:
            if name in self.backends:
                return name, self.backends[name]
        return None


def load_config(path: str | Path = "gateway.yaml") -> GatewayConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return GatewayConfig(**raw)
