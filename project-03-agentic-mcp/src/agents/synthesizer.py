"""Synthesizer agent.

Takes research topic, the plan, and all ResearchFindings.
Single LLM call, no tools. Returns a markdown report with citations.
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI

from src.models import ResearchFinding, ResearchTask

logger = logging.getLogger(__name__)

LLM_BASE_URL = "http://ai.scheidy.com:8082/v1"
MODEL = "Qwen3.6-35B-A3B-MXFP4_MOE.gguf"

SYSTEM_PROMPT = """/no_think
You are a Synthesizer agent. Produce a comprehensive research report from the findings provided.

Structure your report with these sections:
1. Executive Summary (2-3 sentences)
2. Key Findings (one subsection per research task, using the task description as heading)
3. Sources (bulleted list of all URLs cited across findings)
4. Gaps and Limitations (aggregate gaps from all findings)

Write in clear prose. Cite source URLs inline where relevant.
If a finding is partial or low-confidence, note that explicitly in its subsection."""


class SynthesizerAgent:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key="no-key")

    async def run(
        self,
        topic: str,
        plan: list[ResearchTask],
        findings: dict[str, ResearchFinding],
    ) -> str:
        logger.info("Synthesizer processing %d finding(s) for: %s", len(findings), topic)
        prompt = _build_prompt(topic, plan, findings)
        response = await self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
        )
        report = (response.choices[0].message.content or "").strip()
        logger.info("Synthesizer produced %d chars", len(report))
        return report


def _build_prompt(
    topic: str,
    plan: list[ResearchTask],
    findings: dict[str, ResearchFinding],
) -> str:
    task_map = {t.task_id: t for t in plan}
    parts = [f"Research topic: {topic}\n"]

    for task_id, finding in findings.items():
        task = task_map.get(task_id)
        task_desc = task.description if task else task_id
        qualifier = ""
        if finding.partial:
            qualifier = " [PARTIAL — budget or time limit reached]"
        if finding.confidence == "low":
            qualifier += " [LOW CONFIDENCE]"

        parts.append(f"\n---\n**Task:** {task_desc}{qualifier}")
        parts.append(finding.content)

        if finding.sources:
            src_lines = [f"  - {s.url} [{s.tool}]" for s in finding.sources if s.url]
            if src_lines:
                parts.append("Sources:\n" + "\n".join(src_lines))

        if finding.gaps:
            parts.append("Gaps:\n" + "\n".join(f"  - {g}" for g in finding.gaps))

    return "\n".join(parts)
