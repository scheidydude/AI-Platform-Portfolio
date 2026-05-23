from __future__ import annotations
import json
import logging
import sys
import uuid
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
        }
        if isinstance(record.msg, dict):
            base.update(record.msg)
        else:
            base["message"] = record.getMessage()
        return json.dumps(base)


def _build_logger() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    log = logging.getLogger("gateway")
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    log.propagate = False
    return log


logger = _build_logger()


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def log_request(
    *,
    request_id: str,
    team: str,
    model: str,
    backend: str,
    routing_strategy: str,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_tokens: int,
    latency_ms: int,
    status: str,
    quota_remaining: int,
) -> None:
    logger.info({
        "event": "request",
        "request_id": request_id,
        "team": team,
        "model": model,
        "backend": backend,
        "routing_strategy": routing_strategy,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated_tokens": estimated_tokens,
        "latency_ms": latency_ms,
        "status": status,
        "quota_remaining": quota_remaining,
    })
