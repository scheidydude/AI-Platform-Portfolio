"""Planner agent.

Takes a research topic, calls the LLM once (no tools), returns a list of
ResearchTask objects. Falls back to a single generic task if JSON parsing fails.
"""
from __future__ import annotations

import json
import logging
import re

from openai import AsyncOpenAI

from src.models import ResearchTask

logger = logging.getLogger(__name__)

LLM_BASE_URL = "http://ai.scheidy.com:8082/v1"
MODEL = "Qwen3.6-35B-A3B-MXFP4_MOE.gguf"

SYSTEM_PROMPT = """/no_think
You are a Planner agent. Decompose a research topic into 2-4 discrete, focused research tasks.

Return a JSON array. Each element must have exactly these keys:
- "task_id": string like "task_001", "task_002", etc.
- "description": one specific research question (one sentence)
- "success_criteria": array of 2-3 strings describing what a complete answer looks like
- "max_tool_calls": integer between 4 and 8

Return ONLY the JSON array. No explanation, no markdown fences, no other text."""


class PlannerAgent:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key="no-key")

    async def run(self, topic: str) -> list[ResearchTask]:
        logger.info("Planner decomposing topic: %s", topic)
        response = await self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Research topic: {topic}"},
            ],
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or ""
        tasks = _parse_tasks(raw)
        if not tasks:
            logger.warning("Planner JSON parse failed — falling back to single task")
            tasks = [_fallback_task(topic)]
        logger.info("Planner produced %d task(s)", len(tasks))
        return tasks


def _parse_tasks(text: str) -> list[ResearchTask]:
    for candidate in _json_candidates(text.strip()):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list):
            continue
        tasks: list[ResearchTask] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            try:
                tasks.append(ResearchTask(
                    task_id=str(item.get("task_id", f"task_{i+1:03d}")),
                    description=str(item.get("description", "")),
                    success_criteria=[str(c) for c in item.get("success_criteria", [])],
                    max_tool_calls=int(item.get("max_tool_calls", 5)),
                ))
            except (ValueError, TypeError):
                continue
        if tasks:
            return tasks
    return []


def _json_candidates(text: str) -> list[str]:
    candidates = [text]
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        candidates.append(m.group(1).strip())
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        candidates.append(m.group(0))
    return candidates


def _fallback_task(topic: str) -> ResearchTask:
    return ResearchTask(
        task_id="task_001",
        description=topic,
        success_criteria=["Provide a factual overview with sources"],
        max_tool_calls=6,
    )
