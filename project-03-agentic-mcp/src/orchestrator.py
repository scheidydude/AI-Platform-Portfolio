"""Sequential pipeline orchestrator: Planner → Researcher(s) → Synthesizer.

Persists PipelineState to disk (JSON, atomic write) after every transition.
Supports resume: pass the same pipeline_id to skip completed research tasks.

Usage:
    orchestrator = Orchestrator()
    report = await orchestrator.run("your topic")

Resume:
    report = await orchestrator.run("your topic", pipeline_id="abc12345")
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from src.agents.planner import PlannerAgent
from src.agents.researcher import ResearcherAgent
from src.agents.synthesizer import SynthesizerAgent
from src.models import PipelineState

logger = logging.getLogger(__name__)

_DEFAULT_STATE_DIR = Path("state")


class Orchestrator:
    def __init__(self, state_dir: Path = _DEFAULT_STATE_DIR) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(exist_ok=True)
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.synthesizer = SynthesizerAgent()

    async def run(self, topic: str, pipeline_id: str | None = None) -> str:
        pid = pipeline_id or _new_id()
        state = self._load_or_create(pid)
        logger.info("Pipeline %s: status=%s topic=%r", pid, state.status, topic)

        try:
            if state.status == "planning":
                tasks = await self.planner.run(topic)
                state = state.model_copy(update={"plan": tasks})
                state = state.transition("researching")
                self._persist(state)
                logger.info("Pipeline %s: plan has %d task(s)", pid, len(tasks))

            if state.status == "researching":
                completed = set(state.findings.keys())
                for task in state.plan:
                    if task.task_id in completed:
                        logger.info("Pipeline %s: task %s already done — skipping", pid, task.task_id)
                        continue
                    logger.info("Pipeline %s: running task %s", pid, task.task_id)
                    finding = await self.researcher.run(task)
                    state = state.model_copy(update={"findings": {**state.findings, task.task_id: finding}})
                    self._persist(state)
                state = state.transition("synthesizing")
                self._persist(state)

            if state.status == "synthesizing":
                report = await self.synthesizer.run(topic, state.plan, state.findings)
                state = state.transition("complete")
                self._persist(state)
                return report

            if state.status == "complete":
                logger.info("Pipeline %s already complete — re-synthesizing", pid)
                return await self.synthesizer.run(topic, state.plan, state.findings)

        except Exception as exc:
            logger.error("Pipeline %s failed: %s", pid, exc, exc_info=True)
            try:
                failed = state.transition("failed")
                failed = failed.model_copy(update={"error": str(exc)})
                self._persist(failed)
            except ValueError:
                pass  # already in a terminal state
            raise

        return ""  # unreachable; satisfies type checker

    def _load_or_create(self, pipeline_id: str) -> PipelineState:
        path = self.state_dir / f"{pipeline_id}.json"
        if path.exists():
            logger.info("Resuming pipeline %s from disk", pipeline_id)
            return PipelineState.model_validate_json(path.read_text())
        return PipelineState(pipeline_id=pipeline_id)

    def _persist(self, state: PipelineState) -> None:
        path = self.state_dir / f"{state.pipeline_id}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(state.model_dump_json(indent=2))
        os.replace(tmp, path)
        logger.debug("Persisted %s (status=%s)", state.pipeline_id, state.status)


def _new_id() -> str:
    return uuid.uuid4().hex[:8]
