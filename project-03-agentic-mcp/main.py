"""Entry point — run the Researcher agent against a test task.

Usage:
    uv run python main.py
    uv run python main.py "your research question here"
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

from src.agents.researcher import ResearcherAgent
from src.models import AgentConstraints, ResearchTask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

STATE_DIR = Path("state")
STATE_DIR.mkdir(exist_ok=True)


async def main(query: str | None = None) -> None:
    question = query or (
        "What is the Model Context Protocol (MCP) and how does it work? "
        "Who created it and what are its primary use cases?"
    )

    task = ResearchTask(
        task_id=str(uuid.uuid4())[:8],
        description=question,
        success_criteria=[
            "Explain what MCP is in 2–3 sentences",
            "Identify who created MCP",
            "List at least 2 primary use cases",
        ],
        max_tool_calls=5,
    )

    constraints = AgentConstraints(
        max_tool_calls=5,
        max_iterations=15,
        max_wall_time_seconds=120,
        on_exceed="return_partial",
    )

    agent = ResearcherAgent(constraints=constraints)

    print(f"\n{'='*60}")
    print(f"Task: {task.description}")
    print(f"ID:   {task.task_id}")
    print(f"{'='*60}\n")

    finding = await agent.run(task)

    print(f"\n{'='*60}")
    print("FINDING")
    print(f"{'='*60}")
    print(f"Confidence:     {finding.confidence}")
    print(f"Tool calls:     {finding.tool_calls_used}")
    print(f"Sources:        {len(finding.sources)}")
    print(f"Partial:        {finding.partial}")
    print()
    print("Content:")
    print(finding.content)

    if finding.sources:
        print(f"\nSources ({len(finding.sources)}):")
        for s in finding.sources:
            print(f"  [{s.tool}] {s.url}")

    if finding.gaps:
        print(f"\nGaps ({len(finding.gaps)}):")
        for g in finding.gaps:
            print(f"  - {g}")

    # Persist finding to state/
    state_file = STATE_DIR / f"finding_{task.task_id}.json"
    state_file.write_text(finding.model_dump_json(indent=2))
    print(f"\nFinding saved to {state_file}")


if __name__ == "__main__":
    query_arg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    asyncio.run(main(query_arg))
