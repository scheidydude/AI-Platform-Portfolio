"""Experiment 2: Inject garbage tool output (HTML instead of JSON).

Hypothesis: call_tool_safe passes HTML through as success=True because it only
checks MCP isError, not content type. The researcher counts it as progress
(len > 50 chars). The model receives HTML as context and either hallucinates
facts from it or notes that the output is unusable.

Run: uv run python experiments/exp2_garbage_tool_output.py
Requires: llama.cpp server at http://ai.scheidy.com:8082

What to observe:
- finding.partial is likely False (HTML passes the >50 char progress check)
- finding.confidence: depends on whether model catches the garbage
- Does the model hallucinate from the HTML, or does it flag the content?
- Does any gap mention "unreadable" or "HTML"?
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

# Realistic garbage: an HTML error page (what happens when search.scheidy.com
# returns a 500 or the search endpoint returns an nginx error page)
_GARBAGE_HTML = """\
<!DOCTYPE html>
<html><head><title>502 Bad Gateway</title></head>
<body>
<center><h1>502 Bad Gateway</h1></center>
<center>nginx/1.24.0 (Ubuntu)</center>
<hr><center>nginx/1.24.0 (Ubuntu)</center>
</body>
</html>
""" * 3  # repeat to exceed 50-char progress threshold clearly


async def run() -> None:
    from src.agents.researcher import ResearcherAgent

    task = ResearchTask(
        task_id="exp2_garbage",
        description="What is the capital of France and its population?",
        success_criteria=[
            "Name the capital city",
            "Provide current population figure with source",
        ],
        max_tool_calls=4,
    )
    constraints = AgentConstraints(max_tool_calls=4, max_iterations=10, max_wall_time_seconds=90)

    garbage_result = ToolResult(success=True, data=_GARBAGE_HTML)

    print("\n=== EXP 2: GARBAGE TOOL OUTPUT ===")
    print(f"Task: {task.description}")
    print(f"Injected result: {len(_GARBAGE_HTML)} chars of HTML (success=True)\n")

    with patch("src.agents.researcher.call_tool_safe", new=AsyncMock(return_value=garbage_result)):
        researcher = ResearcherAgent(constraints=constraints)
        finding = await researcher.run(task)

    print(f"partial:    {finding.partial}")
    print(f"confidence: {finding.confidence}")
    print(f"tool_calls: {finding.tool_calls_used}")
    print(f"gaps:       {finding.gaps}")
    print(f"\nContent:\n{finding.content}")

    Path("state/exp2_finding.json").write_text(finding.model_dump_json(indent=2))
    print("\n[saved to state/exp2_finding.json]")


if __name__ == "__main__":
    asyncio.run(run())
