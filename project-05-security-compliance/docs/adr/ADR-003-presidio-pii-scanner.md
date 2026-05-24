# ADR-003: Use Microsoft Presidio for Output PII Detection

**Date:** 2026-05-23  
**Status:** Accepted  
**Deciders:** David Scheiderman  
**Project:** Project 05 — Enterprise Security & Compliance

---

## Context

FR-2 requires scanning all model outputs for PII before delivery to the user. We need a detection engine that:
- Identifies a broad set of PII entity types (names, emails, SSNs, financial identifiers)
- Supports confidence scoring to distinguish high-risk from medium-risk findings
- Runs at low latency (< 200ms p95 for responses up to 4096 tokens)
- Is open-source or commercially licensable for a regulated environment
- Can be deployed as a Python library (no external API call required — we cannot send user data to a third-party PII service)

The regulatory context matters: SEC 17a-4(f) and FINRA 4511 require records of all communications. If PII is found in model output and blocked, that blocking event must itself be logged. We need a scanner that gives us structured, loggable results (entity type, position, confidence score, action taken).

---

## Decision

Use **Microsoft Presidio** (`presidio-analyzer`) as the primary PII detection engine, supplemented by regex patterns for financial-domain entities not covered by default Presidio recognizers.

**Entity types to detect:**

| Entity | Risk Level | Action |
|--------|-----------|--------|
| US_SSN | Critical | Block |
| CREDIT_CARD | Critical | Block |
| US_BANK_NUMBER | Critical | Block |
| PERSON | Medium | Warn |
| EMAIL_ADDRESS | Medium | Warn |
| PHONE_NUMBER | Medium | Warn |
| IP_ADDRESS | Low | Log only |

**Confidence threshold:** 0.7 (configurable via environment variable)

**Deployment:** Python library, imported directly into the LLM orchestrator process — no network call, no external API dependency.

**Supplemental regex patterns** for financial-domain entities Presidio may miss:
- CUSIP (9-character alphanumeric securities identifier)
- ISIN (International Securities Identification Number)
- Account numbers in common bank formats

---

## Consequences

**Positive:**
- Production-grade NER-based detection (spaCy backend) — more robust than regex alone for names/emails
- Open-source (MIT license) — no licensing cost, auditable, deployable in regulated environments
- Structured output: entity type, start/end position, confidence score — directly loggable
- Extensible: custom recognizers can be added for domain-specific entities
- No external API call: user data stays within trust boundary

**Negative:**
- Presidio requires spaCy model download at build time (~50MB) — adds to container size
- NER-based PERSON detection has false positive rate on common English words that resemble names
- Presidio does not natively detect all financial-domain identifiers (CUSIP, ISIN) — requires custom recognizers

**Mitigations:**
- False positive rate acceptable at confidence threshold 0.7 for PERSON (warns, does not block)
- CUSIP/ISIN regex recognizers added as Presidio custom recognizers (same API, same output format)
- Container size acceptable in Lambda layer or ECS task; document in deployment guide

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| AWS Comprehend | External API call — user data leaves trust boundary; adds latency; cost at scale |
| Regex only | Insufficient for PERSON names and unstructured PII; high false negative rate |
| Azure AI Language PII | External API call; same trust boundary concern as Comprehend |
| Google DLP | External API call; same concern |
| spaCy NER direct | Would replicate Presidio's entity recognizer framework without the structure; more work for same result |

---

## Implementation Note

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Production initialization — done once at startup, not per-request
provider = NlpEngineProvider(nlp_configuration={"lang_code": "en", "model_name": "en_core_web_lg"})
nlp_engine = provider.create_engine()
registry = RecognizerRegistry()
registry.load_predefined_recognizers()
# register custom CUSIP/ISIN recognizers here
analyzer = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
```

Confidence threshold and entity list should be loaded from environment/config, not hardcoded.

---

*Related: [SRS-001 FR-2](../srs/SRS-001.md), [DESIGN-001 §2.1](../design/DESIGN-001.md)*
