"""
Integration test: Pipeline Regression (FR-3)
SRS: FR-3
DESIGN-001 §4a (happy path sequence diagram)

Tests that:
1. SecureOrchestrator is a drop-in replacement for Orchestrator — same interface,
   same pipeline transitions, same state persistence behavior.
2. Controls are additive: benign input completes without error.
3. PII scan is called on every finding (verified via mock call tracking).
4. SecureOrchestrator.researcher is SecureResearcherAgent (structural check).
5. PIIInFindingError propagates correctly — pipeline transitions to "failed"
   without persisting the PII-containing finding.

LLM and MCP tool calls are mocked so these tests run without a live Qwen3-35B
or SearXNG instance. Presidio is mocked consistent with P05's test strategy.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

import pii_scanner as scanner_module
from pii_scanner import PIIFinding, PIIScanResult
from src.models import ResearchFinding, ResearchTask
from src.orchestrator import Orchestrator

from p06.secure_researcher import (
    PIIInFindingError,
    SecureOrchestrator,
    SecureResearcherAgent,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _presidio_result(entity_type: str, start: int, end: int, score: float = 0.9):
    r = MagicMock()
    r.entity_type = entity_type
    r.start = start
    r.end = end
    r.score = score
    return r


def _benign_finding(task_id: str = "T001") -> ResearchFinding:
    return ResearchFinding(
        task_id=task_id,
        content="Jira is a widely used agile project management tool by Atlassian.",
        confidence="high",
    )


def _pii_finding(task_id: str = "T001") -> ResearchFinding:
    return ResearchFinding(
        task_id=task_id,
        content="The applicant SSN is 123-45-6789 and email is bob@example.com.",
        confidence="high",
    )


def _task(task_id: str = "T001") -> ResearchTask:
    return ResearchTask(
        task_id=task_id,
        description="Describe Jira project management features",
        success_criteria=["List the main Jira features", "Mention Atlassian"],
    )


@pytest.fixture(autouse=True)
def reset_presidio():
    scanner_module._reset_analyzer()
    yield
    scanner_module._reset_analyzer()


@pytest.fixture
def clean_scan_result() -> PIIScanResult:
    return PIIScanResult(has_pii=False, findings=[], action="clean")


@pytest.fixture
def block_scan_result() -> PIIScanResult:
    pii = PIIFinding(entity_type="US_SSN", start=20, end=31, score=0.95)
    return PIIScanResult(has_pii=True, findings=[pii], action="block")


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------

class TestSecureOrchestratorStructure:
    def test_is_orchestrator_subclass(self):
        assert issubclass(SecureOrchestrator, Orchestrator)

    def test_researcher_is_secure_researcher_agent(self, tmp_path):
        orch = SecureOrchestrator(state_dir=tmp_path)
        assert isinstance(orch.researcher, SecureResearcherAgent)

    def test_baseline_orchestrator_uses_base_researcher(self, tmp_path):
        """Baseline still uses ResearcherAgent — SecureOrchestrator does not modify P03."""
        from src.agents.researcher import ResearcherAgent
        base_orch = Orchestrator(state_dir=tmp_path)
        assert type(base_orch.researcher) is ResearcherAgent

    def test_planner_and_synthesizer_unchanged(self, tmp_path):
        """P03's Planner and Synthesizer are inherited without modification."""
        from src.agents.planner import PlannerAgent
        from src.agents.synthesizer import SynthesizerAgent
        orch = SecureOrchestrator(state_dir=tmp_path)
        assert isinstance(orch.planner, PlannerAgent)
        assert isinstance(orch.synthesizer, SynthesizerAgent)


# ---------------------------------------------------------------------------
# Benign pipeline — happy path (FR-3)
# ---------------------------------------------------------------------------

class TestBenignPipelineRegression:
    async def test_benign_pipeline_completes(self, tmp_path, clean_scan_result):
        task = _task("T001")
        finding = _benign_finding("T001")

        with patch(
            "src.agents.planner.PlannerAgent.run",
            new_callable=AsyncMock,
            return_value=[task],
        ), patch(
            "src.agents.researcher.ResearcherAgent.run",
            new_callable=AsyncMock,
            return_value=finding,
        ), patch(
            "src.agents.synthesizer.SynthesizerAgent.run",
            new_callable=AsyncMock,
            return_value="Final report on Jira.",
        ), patch(
            "p06.secure_researcher.scan_output_for_pii",
            return_value=clean_scan_result,
        ):
            orch = SecureOrchestrator(state_dir=tmp_path)
            result = await orch.run("What is Jira?")

        assert result == "Final report on Jira."

    async def test_state_dir_has_pipeline_file(self, tmp_path, clean_scan_result):
        task = _task("T001")
        finding = _benign_finding("T001")

        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("src.agents.synthesizer.SynthesizerAgent.run", new_callable=AsyncMock, return_value="report"), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=clean_scan_result):
            orch = SecureOrchestrator(state_dir=tmp_path)
            await orch.run("What is Jira?")

        state_files = list(tmp_path.glob("*.json"))
        assert len(state_files) == 1

    async def test_pii_scan_called_on_every_finding(self, tmp_path, clean_scan_result):
        tasks = [_task("T001"), _task("T002")]
        findings = [_benign_finding("T001"), _benign_finding("T002")]

        call_count = 0
        original_findings = iter(findings)

        async def mock_researcher_run(task):
            return next(original_findings)

        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=tasks), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, side_effect=mock_researcher_run), \
             patch("src.agents.synthesizer.SynthesizerAgent.run", new_callable=AsyncMock, return_value="report"), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=clean_scan_result) as mock_scan:
            orch = SecureOrchestrator(state_dir=tmp_path)
            await orch.run("What is Jira?")

        assert mock_scan.call_count == 2

    async def test_scan_called_with_finding_content(self, tmp_path, clean_scan_result):
        task = _task("T001")
        finding = _benign_finding("T001")

        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("src.agents.synthesizer.SynthesizerAgent.run", new_callable=AsyncMock, return_value="report"), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=clean_scan_result) as mock_scan:
            orch = SecureOrchestrator(state_dir=tmp_path)
            await orch.run("What is Jira?")

        mock_scan.assert_called_once_with(finding.content)

    async def test_pipeline_status_transitions_to_complete(self, tmp_path, clean_scan_result):
        task = _task("T001")
        finding = _benign_finding("T001")

        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("src.agents.synthesizer.SynthesizerAgent.run", new_callable=AsyncMock, return_value="report"), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=clean_scan_result):
            orch = SecureOrchestrator(state_dir=tmp_path)
            pid = "test_pipeline_abc"
            await orch.run("What is Jira?", pipeline_id=pid)

        state_path = tmp_path / f"{pid}.json"
        import json
        state = json.loads(state_path.read_text())
        assert state["status"] == "complete"


# ---------------------------------------------------------------------------
# PII block — finding not persisted, pipeline fails (DESIGN-001 §4b)
# ---------------------------------------------------------------------------

class TestPIIBlockPath:
    async def test_pii_block_raises_and_pipeline_fails(self, tmp_path, block_scan_result):
        task = _task("T001")
        finding = _pii_finding("T001")

        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=block_scan_result):
            orch = SecureOrchestrator(state_dir=tmp_path)
            pid = "test_pii_block"
            with pytest.raises(PIIInFindingError):
                await orch.run("Sensitive topic", pipeline_id=pid)

    async def test_pii_block_pipeline_state_is_failed(self, tmp_path, block_scan_result):
        task = _task("T001")
        finding = _pii_finding("T001")

        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=block_scan_result):
            orch = SecureOrchestrator(state_dir=tmp_path)
            pid = "test_pii_fail_state"
            with pytest.raises(PIIInFindingError):
                await orch.run("Sensitive topic", pipeline_id=pid)

        import json
        state_path = tmp_path / f"{pid}.json"
        state = json.loads(state_path.read_text())
        assert state["status"] == "failed"

    async def test_pii_finding_not_persisted_in_findings(self, tmp_path, block_scan_result):
        """The PII-containing finding must not appear in persisted state."""
        task = _task("T001")
        finding = _pii_finding("T001")

        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=block_scan_result):
            orch = SecureOrchestrator(state_dir=tmp_path)
            pid = "test_no_pii_persist"
            with pytest.raises(PIIInFindingError):
                await orch.run("Sensitive topic", pipeline_id=pid)

        import json
        state_path = tmp_path / f"{pid}.json"
        state = json.loads(state_path.read_text())
        assert "T001" not in state.get("findings", {})


# ---------------------------------------------------------------------------
# Baseline parity — SecureOrchestrator identical to Orchestrator for benign input
# ---------------------------------------------------------------------------

class TestBaselineParity:
    async def test_same_return_value_as_baseline(self, tmp_path, clean_scan_result):
        """SecureOrchestrator and baseline Orchestrator return identical reports for benign input."""
        task = _task("T001")
        finding = _benign_finding("T001")
        expected_report = "Jira is a project management tool."

        shared_kwargs = dict(
            planner_return=[task],
            researcher_return=finding,
            synthesizer_return=expected_report,
        )

        # Run baseline
        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("src.agents.synthesizer.SynthesizerAgent.run", new_callable=AsyncMock, return_value=expected_report):
            baseline_orch = Orchestrator(state_dir=tmp_path / "baseline")
            baseline_result = await baseline_orch.run("What is Jira?")

        # Run secure
        with patch("src.agents.planner.PlannerAgent.run", new_callable=AsyncMock, return_value=[task]), \
             patch("src.agents.researcher.ResearcherAgent.run", new_callable=AsyncMock, return_value=finding), \
             patch("src.agents.synthesizer.SynthesizerAgent.run", new_callable=AsyncMock, return_value=expected_report), \
             patch("p06.secure_researcher.scan_output_for_pii", return_value=clean_scan_result):
            secure_orch = SecureOrchestrator(state_dir=tmp_path / "secure")
            secure_result = await secure_orch.run("What is Jira?")

        assert baseline_result == secure_result == expected_report
