from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    url: str | None = None
    title: str
    tool: str
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class ResearchTask(BaseModel):
    task_id: str
    description: str
    success_criteria: list[str]
    max_tool_calls: int = 5
    assigned_to: str = "researcher"


class ResearchFinding(BaseModel):
    task_id: str
    content: str
    sources: list[Source] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    gaps: list[str] = Field(default_factory=list)
    tool_calls_used: int = 0
    partial: bool = False


class AgentConstraints(BaseModel):
    max_tool_calls: int = 10
    max_iterations: int = 20
    max_wall_time_seconds: int = 120
    on_exceed: Literal["fail", "return_partial", "escalate"] = "return_partial"
    stall_window: int = 3


class ToolResult(BaseModel):
    success: bool
    data: Any | None = None
    error_class: Literal[
        "rate_limit", "not_found", "timeout", "bad_output", "unavailable"
    ] | None = None
    error_message: str | None = None
    retries_attempted: int = 0


_VALID_TRANSITIONS: dict[str, set[str]] = {
    "planning":    {"researching", "failed"},
    "researching": {"synthesizing", "failed"},
    "synthesizing": {"complete", "failed"},
    "complete":    set(),
    "failed":      set(),
}


class PipelineState(BaseModel):
    pipeline_id: str
    status: Literal[
        "planning", "researching", "synthesizing", "complete", "failed"
    ] = "planning"
    plan: list[ResearchTask] = Field(default_factory=list)
    findings: dict[str, ResearchFinding] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None

    def transition(
        self,
        new_status: Literal["planning", "researching", "synthesizing", "complete", "failed"],
    ) -> "PipelineState":
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid pipeline transition: {self.status!r} → {new_status!r}. "
                f"Allowed: {sorted(allowed) or 'none (terminal state)'}"
            )
        return self.model_copy(update={"status": new_status, "updated_at": datetime.utcnow()})
