"""Experiment 5: Task exceeding researcher context window.

Hypothesis: fetch_page returns very large content → message list grows past
the model's context limit → llama.cpp returns a 400 or truncates silently.
If it raises, the exception propagates through ResearcherAgent.run() uncaught
(only ToolResult errors are caught; LLM API errors are not) → orchestrator
transitions to "failed".

Run: uv run python experiments/exp5_context_overflow.py
Requires: llama.cpp server at http://ai.scheidy.com:8082

What to observe:
- Does llama.cpp truncate silently or return an error?
- If error: does it surface as an openai.APIError or something else?
- Does the orchestrator "failed" state write correctly?
- Is the error message in state JSON interpretable?

Strategy: mock fetch_page to return ~100KB of text, which combined with
the conversation history will exceed Qwen3-35B's practical context.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

load_dotenv()

from src.models import AgentConstraints, ResearchTask, ToolResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

# ~120KB of text — well past any practical context limit
_HUGE_CONTENT = ("Lorem ipsum dolor sit amet. " * 500 + "\n") * 100


def _huge_result(tool_name: str, args: dict) -> ToolResult:
    if tool_name == "fetch_page":
        return ToolResult(success=True, data=_HUGE_CONTENT)
    # Let web_search behave normally (small result) to trigger fetch_page
    return ToolResult(
        success=True,
        data=json.dumps([{
            "url": "https://example.com/huge-page",
            "title": "A very large page",
            "snippet": "This page has a lot of content.",
        }]),
    )


async def run() -> None:
    import json
    from src.agents.researcher import ResearcherAgent
    from src.orchestrator import Orchestrator

    task = ResearchTask(
        task_id="exp5_overflow",
        description="Summarize the content at https://example.com/huge-page",
        success_criteria=["Provide a summary of the page content"],
        max_tool_calls=3,
    )
    constraints = AgentConstraints(max_tool_calls=3, max_iterations=8, max_wall_time_seconds=120)

    print("\n=== EXP 5: CONTEXT WINDOW OVERFLOW ===")
    print(f"Injected fetch_page result: {len(_HUGE_CONTENT):,} chars")
    print(f"Task: {task.description}\n")

    async def fake_call_tool_safe(client, tool_name: str, arguments: dict) -> ToolResult:
        return _huge_result(tool_name, arguments)

    try:
        with patch("src.agents.researcher.call_tool_safe", new=fake_call_tool_safe):
            researcher = ResearcherAgent(constraints=constraints)
            finding = await researcher.run(task)

        print(f"Completed (no exception):")
        print(f"  partial:    {finding.partial}")
        print(f"  confidence: {finding.confidence}")
        print(f"  tool_calls: {finding.tool_calls_used}")
        print(f"  content:    {finding.content[:300]}")
        Path("state/exp5_finding.json").write_text(finding.model_dump_json(indent=2))

    except Exception as exc:
        print(f"Exception raised: {type(exc).__name__}: {exc}")
        print("\nThis is the unhandled path — orchestrator would catch this and")
        print("transition pipeline to 'failed'. The LLM API error is NOT wrapped")
        print("in ToolResult, so it leaks past the error boundary.")


if __name__ == "__main__":
    asyncio.run(run())
