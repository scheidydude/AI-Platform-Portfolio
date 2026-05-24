"""Entry point — run the full 3-agent pipeline (Planner → Researcher → Synthesizer).

Usage:
    uv run python main.py
    uv run python main.py "your research topic"
    uv run python main.py "your research topic" <pipeline_id>   # resume

The pipeline_id is printed at startup. Pass it as the second argument to resume
a pipeline that was interrupted mid-run without re-running completed tasks.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()  # must run before any src imports that read os.environ

from src.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

_DEFAULT_TOPIC = (
    "Find the top Python MCP server implementations on GitHub. "
    "What are the most popular repos, and what patterns do they use?"
)


async def main(topic: str, pipeline_id: str | None = None) -> None:
    orchestrator = Orchestrator()

    print(f"\n{'='*60}")
    print(f"Topic: {topic}")
    if pipeline_id:
        print(f"Resuming pipeline: {pipeline_id}")
    print(f"{'='*60}\n")

    report = await orchestrator.run(topic, pipeline_id)

    print(f"\n{'='*60}")
    print("REPORT")
    print(f"{'='*60}")
    print(report)


if __name__ == "__main__":
    args = sys.argv[1:]
    _topic = args[0] if args else _DEFAULT_TOPIC
    _pipeline_id = args[1] if len(args) > 1 else None
    asyncio.run(main(_topic, _pipeline_id))
