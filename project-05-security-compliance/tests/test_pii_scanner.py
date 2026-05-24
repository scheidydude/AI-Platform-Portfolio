"""
Tests for pii_scanner.py
Control verified: CTRL-06
SRS acceptance criteria: FR-2

Presidio is mocked so these tests run without installing presidio-analyzer.
They validate the decision logic (threshold filtering, action precedence,
entity classification, apply_scan_result) rather than Presidio's NER accuracy.

Run with: pytest tests/test_pii_scanner.py -v
No external dependencies required (Presidio mocked).

Integration tests that exercise real Presidio detection are marked
@pytest.mark.integration and require:
  pip install "presidio-analyzer[nlp]"
  python -m spacy download en_core_web_lg
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import src.pii_scanner as scanner_module
from src.pii_scanner import (
    BLOCK_RESPONSE_TEXT,
    PII_WARNING_HEADER,
    PIIFinding,
    PIIScanResult,
    apply_scan_result,
    scan_output_for_pii,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _presidio_result(entity_type: str, start: int, end: int, score: float):
    """Build a fake Presidio RecognizerResult-like object."""
    r = MagicMock()
    r.entity_type = entity_type
    r.start = start
    r.end = end
    r.score = score
    return r


def _mock_analyzer(results: list) -> MagicMock:
    """Return a mock AnalyzerEngine whose analyze() returns results."""
    mock = MagicMock()
    mock.analyze.return_value = results
    return mock


# ---------------------------------------------------------------------------
# Fixture: reset singleton before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_analyzer_singleton():
    """Ensure module-level _analyzer singleton is reset between tests."""
    scanner_module._reset_analyzer()
    yield
    scanner_module._reset_analyzer()


# ---------------------------------------------------------------------------
# scan_output_for_pii — unit tests (Presidio mocked)
# ---------------------------------------------------------------------------

class TestScanOutputForPii:

    def test_clean_text_returns_clean_result(self):
        mock = _mock_analyzer([])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("The login bug is assigned to the platform team.")

        assert result.action == "clean"
        assert not result.has_pii
        assert result.findings == []

    def test_ssn_triggers_block(self):
        mock = _mock_analyzer([
            _presidio_result("US_SSN", 10, 21, 0.95),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("SSN found: 123-45-6789 in record.")

        assert result.action == "block"
        assert result.has_pii
        assert result.should_block

    def test_credit_card_triggers_block(self):
        mock = _mock_analyzer([
            _presidio_result("CREDIT_CARD", 0, 19, 0.90),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("4111111111111111 is on file.")

        assert result.action == "block"

    def test_bank_account_triggers_block(self):
        mock = _mock_analyzer([
            _presidio_result("US_BANK_NUMBER", 5, 20, 0.85),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("Acct 123456789012345")

        assert result.action == "block"

    def test_email_triggers_warn(self):
        mock = _mock_analyzer([
            _presidio_result("EMAIL_ADDRESS", 16, 33, 0.80),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("Contact assignee jane@corp.com for details.")

        assert result.action == "warn"
        assert result.has_pii
        assert result.should_warn
        assert not result.should_block

    def test_person_name_triggers_warn(self):
        mock = _mock_analyzer([
            _presidio_result("PERSON", 0, 10, 0.75),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("Jane Smith is the assignee.")

        assert result.action == "warn"

    def test_phone_number_triggers_warn(self):
        mock = _mock_analyzer([
            _presidio_result("PHONE_NUMBER", 5, 17, 0.80),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("Call 555-867-5309 for support.")

        assert result.action == "warn"

    def test_below_threshold_ignored(self):
        # Score 0.5 is below default threshold 0.7 — should not be flagged
        mock = _mock_analyzer([
            _presidio_result("PERSON", 0, 4, 0.50),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("Jane is available.")

        assert result.action == "clean"
        assert not result.has_pii

    def test_exactly_at_threshold_included(self):
        mock = _mock_analyzer([
            _presidio_result("EMAIL_ADDRESS", 0, 12, 0.70),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("a@example.com")

        assert result.has_pii
        assert result.action == "warn"

    def test_block_takes_precedence_over_warn(self):
        # Both SSN (block) and EMAIL (warn) present — result must be block
        mock = _mock_analyzer([
            _presidio_result("EMAIL_ADDRESS", 0, 12, 0.80),
            _presidio_result("US_SSN", 20, 31, 0.95),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("a@example.com and 123-45-6789")

        assert result.action == "block"
        assert len(result.findings) == 2

    def test_multiple_warn_entities_all_reported(self):
        mock = _mock_analyzer([
            _presidio_result("EMAIL_ADDRESS", 0, 12, 0.80),
            _presidio_result("PHONE_NUMBER", 17, 29, 0.75),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("a@example.com and 555-867-5309")

        assert result.action == "warn"
        assert len(result.findings) == 2
        entity_types = {f.entity_type for f in result.findings}
        assert "EMAIL_ADDRESS" in entity_types
        assert "PHONE_NUMBER" in entity_types

    def test_custom_confidence_threshold_respected(self):
        # Score 0.75 should be included when threshold is 0.6
        mock = _mock_analyzer([
            _presidio_result("US_SSN", 0, 11, 0.75),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("123-45-6789", confidence_threshold=0.6)

        assert result.has_pii

    def test_custom_high_threshold_excludes_finding(self):
        # Score 0.75 should be excluded when threshold is 0.9
        mock = _mock_analyzer([
            _presidio_result("US_SSN", 0, 11, 0.75),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("123-45-6789", confidence_threshold=0.9)

        assert not result.has_pii
        assert result.action == "clean"

    def test_entity_types_found_populated(self):
        mock = _mock_analyzer([
            _presidio_result("EMAIL_ADDRESS", 0, 12, 0.80),
        ])
        scanner_module._analyzer = mock

        result = scan_output_for_pii("a@example.com")

        assert "EMAIL_ADDRESS" in result.entity_types_found


# ---------------------------------------------------------------------------
# Regex recognizers — CUSIP and ISIN (no mock needed)
# ---------------------------------------------------------------------------

class TestRegexRecognizers:
    """
    CUSIP and ISIN are detected by regex without Presidio.
    These tests require no mocking.
    """

    @pytest.fixture(autouse=True)
    def mock_presidio_clean(self):
        """Return empty Presidio results so only regex findings are tested."""
        mock = _mock_analyzer([])
        scanner_module._analyzer = mock

    def test_cusip_triggers_block(self):
        # 037833100 is a well-known CUSIP (Apple Inc.)
        result = scan_output_for_pii("The security CUSIP is 037833100.")
        assert result.has_pii
        assert result.action == "block"
        assert any(f.entity_type == "CUSIP" for f in result.findings)

    def test_isin_triggers_block(self):
        # US0378331005 is Apple Inc. ISIN
        result = scan_output_for_pii("ISIN: US0378331005 was retrieved.")
        assert result.has_pii
        assert result.action == "block"
        assert any(f.entity_type == "ISIN" for f in result.findings)

    def test_no_false_positive_on_random_text(self):
        result = scan_output_for_pii("The ticket status is In Progress.")
        assert not result.has_pii


# ---------------------------------------------------------------------------
# apply_scan_result
# ---------------------------------------------------------------------------

class TestApplyScanResult:

    def _clean_result(self) -> PIIScanResult:
        return PIIScanResult(has_pii=False, findings=[], action="clean")

    def _warn_result(self, entity_types: list[str]) -> PIIScanResult:
        findings = [
            PIIFinding(entity_type=et, start=0, end=5, score=0.80)
            for et in entity_types
        ]
        return PIIScanResult(
            has_pii=True,
            findings=findings,
            action="warn",
            entity_types_found=entity_types,
        )

    def _block_result(self) -> PIIScanResult:
        findings = [PIIFinding(entity_type="US_SSN", start=0, end=11, score=0.95)]
        return PIIScanResult(
            has_pii=True,
            findings=findings,
            action="block",
            entity_types_found=["US_SSN"],
        )

    def test_clean_returns_original_text_no_headers(self):
        text = "The bug is in the auth service."
        final, headers = apply_scan_result(text, self._clean_result())
        assert final == text
        assert headers == {}

    def test_warn_returns_original_text_with_warning_header(self):
        text = "Assignee: jane@corp.com"
        final, headers = apply_scan_result(text, self._warn_result(["EMAIL_ADDRESS"]))
        assert final == text
        assert PII_WARNING_HEADER in headers
        assert "EMAIL_ADDRESS" in headers[PII_WARNING_HEADER]

    def test_warn_header_contains_all_entity_types(self):
        result = self._warn_result(["EMAIL_ADDRESS", "PHONE_NUMBER"])
        _, headers = apply_scan_result("text", result)
        header_val = headers[PII_WARNING_HEADER]
        assert "EMAIL_ADDRESS" in header_val
        assert "PHONE_NUMBER" in header_val

    def test_block_returns_safe_message_not_original(self):
        original = "SSN: 123-45-6789"
        final, headers = apply_scan_result(original, self._block_result())
        assert final != original
        assert final == BLOCK_RESPONSE_TEXT
        assert "123-45-6789" not in final

    def test_block_sets_blocked_header(self):
        _, headers = apply_scan_result("text", self._block_result())
        assert headers[PII_WARNING_HEADER] == "blocked"

    def test_block_message_is_user_safe(self):
        final, _ = apply_scan_result("secret data", self._block_result())
        # Must not leak entity types or values in the user-facing message
        assert "SSN" not in final
        assert "secret" not in final


# ---------------------------------------------------------------------------
# PIIFinding.action property
# ---------------------------------------------------------------------------

class TestPIIFindingAction:
    def test_ssn_action_is_block(self):
        f = PIIFinding(entity_type="US_SSN", start=0, end=11, score=0.9)
        assert f.action == "block"

    def test_email_action_is_warn(self):
        f = PIIFinding(entity_type="EMAIL_ADDRESS", start=0, end=12, score=0.8)
        assert f.action == "warn"

    def test_cusip_action_is_block(self):
        f = PIIFinding(entity_type="CUSIP", start=0, end=9, score=0.85)
        assert f.action == "block"

    def test_isin_action_is_block(self):
        f = PIIFinding(entity_type="ISIN", start=0, end=12, score=0.85)
        assert f.action == "block"
