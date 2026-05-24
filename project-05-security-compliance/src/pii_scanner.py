"""
Output PII Scanner
Control: CTRL-06
Threats mitigated: I-01, I-03, R-03
SRS reference: FR-2
ADR reference: ADR-003

All model outputs pass through scan_output_for_pii() before delivery to the
user. Presidio (Microsoft) provides NER-based entity detection backed by
spaCy. Custom regex recognizers cover financial-domain identifiers (CUSIP,
ISIN) that Presidio's default recognizers do not handle.

Entity → action mapping:
  block  US_SSN, CREDIT_CARD, US_BANK_NUMBER, CUSIP, ISIN
  warn   PERSON, EMAIL_ADDRESS, PHONE_NUMBER, IP_ADDRESS

Blocked responses are replaced with a safe error message. Warned responses
are delivered with an X-PII-Warning header. Both events are logged.

Dependencies:
  presidio-analyzer>=2.2
  presidio-analyzer[nlp]   (installs spaCy + en_core_web_lg)

  pip install "presidio-analyzer[nlp]"
  python -m spacy download en_core_web_lg
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Entity classification
# ---------------------------------------------------------------------------

BLOCK_ENTITY_TYPES: frozenset[str] = frozenset({
    "US_SSN",
    "CREDIT_CARD",
    "US_BANK_NUMBER",
    "CUSIP",
    "ISIN",
})

WARN_ENTITY_TYPES: frozenset[str] = frozenset({
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IP_ADDRESS",
})

ALL_ENTITY_TYPES: frozenset[str] = BLOCK_ENTITY_TYPES | WARN_ENTITY_TYPES

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.7

BLOCK_RESPONSE_TEXT = (
    "Response blocked: the AI assistant detected sensitive information "
    "in the generated response. The response was not delivered. "
    "Please rephrase your request or contact your administrator."
)

PII_WARNING_HEADER = "X-PII-Warning"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PIIFinding:
    """A single PII entity detected in the output text."""
    entity_type: str
    start: int
    end: int
    score: float

    @property
    def action(self) -> str:
        if self.entity_type in BLOCK_ENTITY_TYPES:
            return "block"
        if self.entity_type in WARN_ENTITY_TYPES:
            return "warn"
        return "log"


@dataclass
class PIIScanResult:
    """Result of scanning a model output for PII."""
    has_pii: bool
    findings: list[PIIFinding]
    action: str          # "clean" | "warn" | "block"
    entity_types_found: list[str] = field(default_factory=list)

    @property
    def should_block(self) -> bool:
        return self.action == "block"

    @property
    def should_warn(self) -> bool:
        return self.action == "warn"


# ---------------------------------------------------------------------------
# Custom regex recognizers for financial-domain entities
# ---------------------------------------------------------------------------

# CUSIP: 9 characters — 6 alphanumeric issuer, 2 alphanumeric issue, 1 check digit
_CUSIP_RE = re.compile(r"\b[0-9]{3}[A-Z0-9]{5}[0-9]\b")

# ISIN: 2-letter country code + 10 alphanumeric + 1 check digit
_ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")


def _scan_regex_entities(text: str, threshold: float) -> list[PIIFinding]:
    """Find CUSIP and ISIN patterns via regex (Presidio custom recognizer equivalent)."""
    findings: list[PIIFinding] = []
    for m in _CUSIP_RE.finditer(text):
        findings.append(PIIFinding(
            entity_type="CUSIP",
            start=m.start(),
            end=m.end(),
            score=0.85,
        ))
    for m in _ISIN_RE.finditer(text):
        findings.append(PIIFinding(
            entity_type="ISIN",
            start=m.start(),
            end=m.end(),
            score=0.85,
        ))
    return [f for f in findings if f.score >= threshold]


# ---------------------------------------------------------------------------
# Presidio analyzer — lazy singleton
# ---------------------------------------------------------------------------

_analyzer = None


def _get_analyzer():
    """
    Return the module-level Presidio AnalyzerEngine singleton.
    Initialized on first call; subsequent calls return the cached instance.
    Raises ImportError with a clear message if presidio-analyzer is not installed.
    """
    global _analyzer
    if _analyzer is not None:
        return _analyzer

    try:
        from presidio_analyzer import AnalyzerEngine  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "presidio-analyzer is required for PII scanning. "
            "Install with: pip install 'presidio-analyzer[nlp]' "
            "then: python -m spacy download en_core_web_lg"
        ) from exc

    _analyzer = AnalyzerEngine()
    return _analyzer


def _reset_analyzer() -> None:
    """Reset the singleton — used in tests to inject a mock."""
    global _analyzer
    _analyzer = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_output_for_pii(
    text: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> PIIScanResult:
    """
    CTRL-06: Scan model output text for PII before delivery.

    Combines Presidio NER detection with regex recognizers for financial-domain
    identifiers. Returns a PIIScanResult describing what was found and what
    action to take.

    Action precedence: block > warn > clean
      - Any BLOCK_ENTITY_TYPES finding → action = "block"
      - Any WARN_ENTITY_TYPES finding (no block) → action = "warn"
      - No findings above threshold → action = "clean"
    """
    analyzer = _get_analyzer()

    raw_results = analyzer.analyze(
        text=text,
        entities=list(ALL_ENTITY_TYPES - {"CUSIP", "ISIN"}),  # regex handles these
        language="en",
    )

    presidio_findings = [
        PIIFinding(
            entity_type=r.entity_type,
            start=r.start,
            end=r.end,
            score=r.score,
        )
        for r in raw_results
        if r.score >= confidence_threshold
    ]

    regex_findings = _scan_regex_entities(text, confidence_threshold)
    all_findings = presidio_findings + regex_findings

    if not all_findings:
        return PIIScanResult(has_pii=False, findings=[], action="clean")

    entity_types = [f.entity_type for f in all_findings]
    if any(f.entity_type in BLOCK_ENTITY_TYPES for f in all_findings):
        action = "block"
    else:
        action = "warn"

    return PIIScanResult(
        has_pii=True,
        findings=all_findings,
        action=action,
        entity_types_found=entity_types,
    )


def apply_scan_result(
    response_text: str,
    result: PIIScanResult,
) -> tuple[str, dict[str, str]]:
    """
    Apply a scan result to produce the final response text and HTTP headers.

    Returns:
        (final_text, headers)
        - On "clean": (original text, {})
        - On "warn":  (original text, {X-PII-Warning: comma-sep entity types})
        - On "block": (BLOCK_RESPONSE_TEXT, {X-PII-Warning: "blocked"})
    """
    if result.action == "clean":
        return response_text, {}

    if result.action == "warn":
        entity_list = ", ".join(sorted(set(result.entity_types_found)))
        return response_text, {PII_WARNING_HEADER: entity_list}

    # block
    return BLOCK_RESPONSE_TEXT, {PII_WARNING_HEADER: "blocked"}
