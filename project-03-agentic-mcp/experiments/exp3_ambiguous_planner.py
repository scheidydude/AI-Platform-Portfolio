"""Experiment 3: Ambiguous planner input.

Hypothesis: vague topics produce vague tasks with overlapping or untestable
success criteria. The planner makes a best-guess decomposition rather than
asking for clarification (no clarification mechanism exists). Resulting tasks
may be too broad for the tool budget.

Run: uv run python experiments/exp3_ambiguous_planner.py
Requires: llama.cpp server at http://ai.scheidy.com:8082

What to observe:
- Do tasks overlap (same question rephrased)?
- Are success criteria specific enough to verify?
- Does the planner split into subtopics or produce one vague mega-task?
- Does the fallback fire (parse failure)?
"""
from __future__ import annotations

import asyncio
import json
import logging

from dotenv import load_dotenv

load_dotenv()

from src.agents.planner import PlannerAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

AMBIGUOUS_TOPICS = [
    "Everything about AI",
    "How does technology work?",
    "Tell me about programming",
]


async def run() -> None:
    planner = PlannerAgent()

    print("\n=== EXP 3: AMBIGUOUS PLANNER INPUT ===\n")
    for topic in AMBIGUOUS_TOPICS:
        print(f"Topic: {topic!r}")
        tasks = await planner.run(topic)
        print(f"Tasks produced: {len(tasks)}")
        for t in tasks:
            print(f"  [{t.task_id}] {t.description}")
            for c in t.success_criteria:
                print(f"    - {c}")
            print(f"    budget: {t.max_tool_calls}")
        print()

        # Flag overlapping tasks (same significant words in description)
        if len(tasks) > 1:
            descriptions = [t.description.lower().split() for t in tasks]
            for i, d1 in enumerate(descriptions):
                for j, d2 in enumerate(descriptions):
                    if i >= j:
                        continue
                    common = set(w for w in d1 if len(w) > 4) & set(w for w in d2 if len(w) > 4)
                    if len(common) >= 3:
                        print(f"  ⚠ Possible overlap between task {i+1} and {j+1}: {common}")


if __name__ == "__main__":
    asyncio.run(run())
