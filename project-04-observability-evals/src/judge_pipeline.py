"""LLM-as-judge pipeline.

Scores a single SUT output against an eval case's expected specification.
Model: claude-sonnet-4-6 (separate from SUT per ADR-0001).
Judge prompt: eval/prompts/judge_v1.md (versioned, cached per run).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
import anthropic

_JUDGE_PROMPT_PATH = Path(__file__).parent.parent / "eval" / "prompts" / "judge_v1.md"

_client: anthropic.Anthropic | None = None
_judge_system_prompt: str | None = None

_FALLBACK_JUDGMENT = {
    "scores": {
        "faithfulness": 1,
        "task_completion": 1,
        "tone": 1,
        "compliance": "fail",
        "overall": 1,
    },
    "reasoning": "Judge output could not be parsed.",
    "flags": ["PARSE_ERROR"],
    "pass": False,
}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _load_judge_prompt() -> str:
    global _judge_system_prompt
    if _judge_system_prompt is None:
        _judge_system_prompt = _JUDGE_PROMPT_PATH.read_text()
    return _judge_system_prompt


def _build_judge_input(case: dict, sut_output: dict) -> str:
    return json.dumps(
        {
            "case_id": case["id"],
            "category": case["category"],
            "priority": case["priority"],
            "behaviors": case["behaviors"],
            "input": case["input"],
            "expected": case["expected"],
            "sut_output": sut_output,
        },
        indent=2,
    )


def _parse_judgment(text: str, case_id: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            judgment = json.loads(match.group())
            judgment["case_id"] = case_id
            return judgment
        except json.JSONDecodeError:
            pass
    result = dict(_FALLBACK_JUDGMENT)
    result["case_id"] = case_id
    result["raw"] = text
    return result


def judge_case(case: dict, sut_output: dict) -> dict:
    """Score a single SUT output. Returns judgment dict."""
    client = _get_client()
    system_prompt = _load_judge_prompt()
    user_message = _build_judge_input(case, sut_output)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    return _parse_judgment(response.content[0].text, case["id"])
