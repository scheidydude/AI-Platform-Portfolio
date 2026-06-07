"""
Integration test: PII Scan on ResearchFinding (Wiring Point 2)
SRS: FR-2
DESIGN-001 §3 Wiring Point 2, §4b

Tests that:
1. scan_output_for_pii() correctly identifies PII in a ResearchFinding.content string
   that represents real P03 output — not just synthetic test inputs.
2. PIIInFindingError is raised by SecureResearcherAgent.run() on action="block".
3. Warn-level PII (EMAIL_ADDRESS) passes through with a warning, not a block.
4. Benign findings pass through unchanged.

Presidio is mocked (same strategy as P05's own test suite) so these tests run
without installing presidio-analyzer or en_core_web_lg. The mock validates P06's
integration logic (error handling, action routing, finding pass-through) rather
than Presidio's NER accuracy — that is covered by P05's 27 tests.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pii_scanner as scanner_module
from pii_scanner import PIIFinding, PIIScanResult, scan_output_for_pii
from src.models import ResearchFinding, ResearchTask

from p06.secure_researcher import PIIInFindingError, SecureResearcherAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _presidio_result(entity_type: str, start: int, end: int, score: float = 0.9):
    r = MagicMock()
    r.entity_type = entity_type
    r.start = start
    r.end = end
    r.score = score
    return r


def _mock_analyzer(*presidio_results) -> MagicMock:
    mock = MagicMock()
    mock.analyze.return_value = list(presidio_results)
    return mock


def _finding(content: str, task_id: str = "T001") -> ResearchFinding:
    return ResearchFinding(
        task_id=task_id,
        content=content,
        confidence="high",
    )


def _task(task_id: str = "T001") -> ResearchTask:
    return ResearchTask(
        task_id=task_id,
        description="Research Jira features",
        success_criteria=["Describe the main Jira features"],
    )


@pytest.fixture(autouse=True)
def reset_presidio_singleton():
    """Reset Presidio analyzer singleton before each test — prevents state leak."""
    scanner_module._reset_analyzer()
    yield
    scanner_module._reset_analyzer()


# ---------------------------------------------------------------------------
# scan_output_for_pii on ResearchFinding content
# ---------------------------------------------------------------------------

class TestScanFindingContent:
    def test_ssn_blocked(self):
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("US_SSN", 20, 31, 0.95)
        )
        finding = _finding("The applicant SSN is 123-45-6789.")
        result = scan_output_for_pii(finding.content)
        assert result.has_pii is True
        assert result.action == "block"
        assert any(f.entity_type == "US_SSN" for f in result.findings)

    def test_ssn_and_email_both_blocked(self):
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("US_SSN", 20, 31, 0.95),
            _presidio_result("EMAIL_ADDRESS", 50, 67, 0.9),
        )
        finding = _finding(
            "The applicant SSN is 123-45-6789 and can be reached at bob@example.com."
        )
        result = scan_output_for_pii(finding.content)
        assert result.has_pii is True
        assert result.action == "block"
        entity_types = [f.entity_type for f in result.findings]
        assert "US_SSN" in entity_types
        assert "EMAIL_ADDRESS" in entity_types

    def test_email_only_warns(self):
        """EMAIL_ADDRESS is a warn-level entity — should not block."""
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("EMAIL_ADDRESS", 30, 47, 0.9),
        )
        finding = _finding("The contact email is alice@example.com.")
        result = scan_output_for_pii(finding.content)
        assert result.has_pii is True
        assert result.action == "warn"
        assert not result.should_block

    def test_benign_finding_clean(self):
        scanner_module._analyzer = _mock_analyzer()  # no results
        finding = _finding("Jira is a project management tool by Atlassian.")
        result = scan_output_for_pii(finding.content)
        assert result.has_pii is False
        assert result.action == "clean"
        assert result.findings == []

    def test_credit_card_blocked(self):
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("CREDIT_CARD", 10, 29, 0.95),
        )
        finding = _finding("Card number 4111-1111-1111-1111 on file.")
        result = scan_output_for_pii(finding.content)
        assert result.action == "block"

    def test_below_threshold_not_flagged(self):
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("US_SSN", 5, 16, 0.4),  # below 0.7 threshold
        )
        finding = _finding("Maybe 123-45-6789.")
        result = scan_output_for_pii(finding.content)
        assert result.has_pii is False


# ---------------------------------------------------------------------------
# SecureResearcherAgent.run() — PII error raised on block
# ---------------------------------------------------------------------------

class TestSecureResearcherAgentPIIBlock:
    @pytest.fixture
    def pii_finding(self):
        return _finding("The applicant SSN is 123-45-6789.", task_id="T_PII")

    @pytest.fixture
    def benign_finding(self):
        return _finding("Jira is used for agile project tracking.", task_id="T_OK")

    async def test_block_raises_pii_error(self, pii_finding):
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("US_SSN", 20, 31, 0.95)
        )
        agent = SecureResearcherAgent()
        task = _task("T_PII")
        with patch(
            "src.agents.researcher.ResearcherAgent.run",
            new_callable=AsyncMock,
            return_value=pii_finding,
        ):
            with pytest.raises(PIIInFindingError) as exc_info:
                await agent.run(task)
        assert exc_info.value.task_id == "T_PII"

    async def test_block_error_contains_entity_types(self, pii_finding):
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("US_SSN", 20, 31, 0.95)
        )
        agent = SecureResearcherAgent()
        task = _task("T_PII")
        with patch(
            "src.agents.researcher.ResearcherAgent.run",
            new_callable=AsyncMock,
            return_value=pii_finding,
        ):
            with pytest.raises(PIIInFindingError) as exc_info:
                await agent.run(task)
        entity_types = [f.entity_type for f in exc_info.value.pii_findings]
        assert "US_SSN" in entity_types

    async def test_benign_finding_returned_unchanged(self, benign_finding):
        scanner_module._analyzer = _mock_analyzer()  # no PII
        agent = SecureResearcherAgent()
        task = _task("T_OK")
        with patch(
            "src.agents.researcher.ResearcherAgent.run",
            new_callable=AsyncMock,
            return_value=benign_finding,
        ):
            result = await agent.run(task)
        assert result is benign_finding
        assert result.content == "Jira is used for agile project tracking."

    async def test_warn_finding_passes_through(self, tmp_path):
        scanner_module._analyzer = _mock_analyzer(
            _presidio_result("EMAIL_ADDRESS", 30, 47, 0.9),
        )
        warn_finding = _finding("Contact is alice@example.com.", task_id="T_WARN")
        agent = SecureResearcherAgent()
        task = _task("T_WARN")
        with patch(
            "src.agents.researcher.ResearcherAgent.run",
            new_callable=AsyncMock,
            return_value=warn_finding,
        ):
            result = await agent.run(task)
        # warn does not raise — finding is returned
        assert result is warn_finding

    async def test_scan_called_with_finding_content(self, benign_finding):
        scanner_module._analyzer = _mock_analyzer()
        agent = SecureResearcherAgent()
        task = _task("T_OK")
        with patch(
            "src.agents.researcher.ResearcherAgent.run",
            new_callable=AsyncMock,
            return_value=benign_finding,
        ), patch(
            "p06.secure_researcher.scan_output_for_pii",
            wraps=scan_output_for_pii,
        ) as mock_scan:
            await agent.run(task)
        mock_scan.assert_called_once_with(benign_finding.content)


# ---------------------------------------------------------------------------
# PIIInFindingError construction
# ---------------------------------------------------------------------------

class TestPIIInFindingError:
    def test_task_id_stored(self):
        pii = PIIFinding(entity_type="US_SSN", start=0, end=11, score=0.95)
        err = PIIInFindingError("T001", [pii])
        assert err.task_id == "T001"

    def test_pii_findings_stored(self):
        pii = PIIFinding(entity_type="CREDIT_CARD", start=0, end=16, score=0.95)
        err = PIIInFindingError("T002", [pii])
        assert len(err.pii_findings) == 1
        assert err.pii_findings[0].entity_type == "CREDIT_CARD"

    def test_message_contains_task_id(self):
        pii = PIIFinding(entity_type="US_SSN", start=0, end=11, score=0.95)
        err = PIIInFindingError("TASK_XYZ", [pii])
        assert "TASK_XYZ" in str(err)

    def test_message_contains_entity_type(self):
        pii = PIIFinding(entity_type="US_SSN", start=0, end=11, score=0.95)
        err = PIIInFindingError("T001", [pii])
        assert "US_SSN" in str(err)

    def test_is_exception(self):
        pii = PIIFinding(entity_type="US_SSN", start=0, end=11, score=0.95)
        err = PIIInFindingError("T001", [pii])
        assert isinstance(err, Exception)
