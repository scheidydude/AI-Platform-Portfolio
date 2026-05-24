"""Experiment 1: Exhaust researcher tool budget mid-task.

Hypothesis: researcher returns partial=True with low-confidence content;
synthesizer receives the degraded finding and must note the gap explicitly.

Run: uv run python experiments/exp1_budget_exhaustion.py
Requires: llama.cpp server at http://ai.scheidy.com:8082, SearXNG + GitHub MCP

What to observe:
- finding.partial == True
- finding.confidence == "low"
- finding.gaps is non-empty
- synthesizer report acknowledges the gap (look for "partial" or "limitation")
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.agents.researcher import ResearcherAgent
from src.agents.synthesizer import SynthesizerAgent
from src.models import AgentConstraints, ResearchTask

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")


async def run() -> None:
    # 1 tool call budget on a 3-criterion task — guaranteed to be partial
    task = ResearchTask(
        task_id="exp1_budget",
        description=(
            "What are the main Python web frameworks? "
            "Compare Flask, Django, and FastAPI."
        ),
        success_criteria=[
            "Describe Flask's design philosophy",
            "Describe Django's design philosophy",
            "Describe FastAPI's design philosophy",
        ],
        max_tool_calls=1,
    )
    constraints = AgentConstraints(
        max_tool_calls=1,
        max_iterations=5,
        max_wall_time_seconds=60,
        on_exceed="return_partial",
    )

    print("\n=== EXP 1: BUDGET EXHAUSTION ===")
    print(f"Task: {task.description}")
    print(f"Budget: {task.max_tool_calls} tool call\n")

    researcher = ResearcherAgent(constraints=constraints)
    finding = await researcher.run(task)

    print(f"partial:    {finding.partial}")
    print(f"confidence: {finding.confidence}")
    print(f"tool_calls: {finding.tool_calls_used}")
    print(f"gaps:       {finding.gaps}")
    print(f"\nContent ({len(finding.content)} chars):\n{finding.content[:500]}...")

    print("\n=== SYNTHESIZER WITH PARTIAL INPUT ===")
    synthesizer = SynthesizerAgent()
    plan = [task]
    report = await synthesizer.run(task.description, plan, {task.task_id: finding})
    print(report[:1000])

    Path("state/exp1_finding.json").write_text(finding.model_dump_json(indent=2))
    print("\n[saved to state/exp1_finding.json]")


if __name__ == "__main__":
    asyncio.run(run())
