"""Production metrics emitter — DogStatsD format.

Emits judge scores and request signals after scoring a production request.
See docs/design/monitoring-design.md §4 for full metric definitions.

Modes (controlled by environment variables):
  - stdout (default): no external dependency; usable in dev and CI
  - UDP: set DOGSTATSD_HOST (and optionally DOGSTATSD_PORT, default 8125)

Usage:
    from metrics_emitter import emit_judgment

    emit_judgment(
        judgment={"scores": {"faithfulness": 4, ...}, "pass": True, "flags": []},
        request_meta={
            "ticket_type": "incident",
            "sampling_reason": "base_rate",
            "model_version": "haiku-4-5",
            "prompt_version": "sut_v1",
            "judge_prompt": "judge_v1",
            "env": "production",
        },
    )
"""
from __future__ import annotations

import os
import socket
import time


_DOGSTATSD_HOST = os.environ.get("DOGSTATSD_HOST")
_DOGSTATSD_PORT = int(os.environ.get("DOGSTATSD_PORT", "8125"))

_sock: socket.socket | None = None


def _get_socket() -> socket.socket:
    global _sock
    if _sock is None:
        _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return _sock


def _tag_str(tags: dict[str, str]) -> str:
    return "|#" + ",".join(f"{k}:{v}" for k, v in tags.items() if v) if tags else ""


def _send(metric: str, value: float | int, metric_type: str, tags: dict[str, str]) -> None:
    """Format and dispatch a single DogStatsD metric."""
    payload = f"{metric}:{value}|{metric_type}{_tag_str(tags)}"
    if _DOGSTATSD_HOST:
        try:
            _get_socket().sendto(payload.encode(), (_DOGSTATSD_HOST, _DOGSTATSD_PORT))
        except OSError:
            pass
    else:
        print(f"[metrics] {payload}")


def emit_judgment(judgment: dict, request_meta: dict) -> None:
    """Emit all metrics for a single judged production request.

    Args:
        judgment: output from judge_pipeline.judge_case()
        request_meta: dict with keys: ticket_type, sampling_reason,
            model_version, prompt_version, judge_prompt, env.
            All keys are optional; missing values are tagged as "unknown".
    """
    base_tags: dict[str, str] = {
        "ticket_type": request_meta.get("ticket_type") or "unknown",
        "sampling_reason": request_meta.get("sampling_reason") or "unknown",
        "model_version": request_meta.get("model_version") or "unknown",
        "prompt_version": request_meta.get("prompt_version") or "unknown",
        "judge_prompt": request_meta.get("judge_prompt") or "unknown",
        "env": request_meta.get("env") or "production",
    }

    scores = judgment.get("scores", {})

    # Continuous score dimensions (gauge 1–5)
    for dim in ("faithfulness", "task_completion", "tone", "overall"):
        val = scores.get(dim)
        if isinstance(val, (int, float)):
            _send(f"helpdesk.judge.{dim}", val, "g", base_tags)

    # Compliance (count, tagged by result)
    compliance = scores.get("compliance")
    if compliance in ("pass", "fail"):
        comp_tags = {**base_tags, "result": compliance}
        _send("helpdesk.judge.compliance", 1, "c", comp_tags)

    # Request sampled counter
    _send("helpdesk.request.sampled", 1, "c", base_tags)

    # Request judged counter (tagged by pass/fail)
    passed = judgment.get("pass", False)
    judged_tags = {**base_tags, "pass": "true" if passed else "false"}
    _send("helpdesk.request.judged", 1, "c", judged_tags)

    # Escalation counter
    if request_meta.get("escalated"):
        _send("helpdesk.request.escalated", 1, "c", base_tags)

    # Judge call latency (if provided)
    latency_ms = request_meta.get("judge_latency_ms")
    if isinstance(latency_ms, (int, float)):
        _send("helpdesk.judge.latency_ms", latency_ms, "h", base_tags)

    # Per-flag counters (for debugging specific failure modes)
    for flag in judgment.get("flags", []):
        flag_tags = {**base_tags, "flag": flag.lower()}
        _send("helpdesk.judge.flag", 1, "c", flag_tags)


def emit_judge_error(request_meta: dict, error: str = "") -> None:
    """Emit a counter when the judge call itself fails (API error, parse error)."""
    tags: dict[str, str] = {
        "env": request_meta.get("env") or "production",
        "sampling_reason": request_meta.get("sampling_reason") or "unknown",
        "error": error[:40] if error else "unknown",
    }
    _send("helpdesk.request.judge_error", 1, "c", tags)


def emit_sample_decision(sampled: bool, reason: str, request_meta: dict) -> None:
    """Emit a counter for every request, regardless of whether it was sampled.

    Allows computing the true sampling rate from Datadog.
    """
    tags: dict[str, str] = {
        "sampled": "true" if sampled else "false",
        "reason": reason or "not_sampled",
        "env": request_meta.get("env") or "production",
    }
    _send("helpdesk.request.evaluated", 1, "c", tags)


if __name__ == "__main__":
    # Demo: emit a sample judgment to stdout
    demo_judgment = {
        "scores": {
            "faithfulness": 4,
            "task_completion": 5,
            "tone": 4,
            "compliance": "pass",
            "overall": 4,
        },
        "reasoning": "Correct incident classification. No PII in ticket.",
        "flags": [],
        "pass": True,
    }
    demo_meta = {
        "ticket_type": "incident",
        "sampling_reason": "base_rate",
        "model_version": "haiku-4-5",
        "prompt_version": "sut_v1",
        "judge_prompt": "judge_v1",
        "env": "demo",
        "judge_latency_ms": 1240,
    }
    print("Demo emit (stdout mode):\n")
    emit_judgment(demo_judgment, demo_meta)
    emit_sample_decision(sampled=True, reason="base_rate", request_meta=demo_meta)
