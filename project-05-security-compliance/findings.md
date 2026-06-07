# Findings & Decisions

## Requirements
- Formal threat model for enterprise AI deployment (Jira/Confluence assistant)
- STRIDE adapted to LLM attack surface
- Working implementations of at least 2 controls
- Compliance mapping: SEC 17a-4(f), FINRA 4511, SOC 2 Type II
- Portfolio-grade output — publishable artifact

## System Boundary (Phase 1 Findings)
Components in scope:
- User interface (web or Slack)
- API gateway / authentication layer
- LLM inference endpoint (AWS Bedrock)
- Tool execution layer (MCP servers)
- Data sources (Confluence, Jira)
- Logging and audit infrastructure
- Model context (system prompt, conversation history)

## Data Classification
| Data type | Classification | In model context? | Sensitivity |
|---|---|---|---|
| User query text | Internal | Yes | Medium |
| System prompt | Confidential | Yes | High |
| Confluence article content | Internal | Yes (retrieved) | Medium |
| Jira ticket content | Internal | Yes (retrieved) | Medium |
| User PII from query | Restricted | Potentially | Critical |
| Model outputs | Internal | Yes (history) | Medium |
| API keys / credentials | Secret | Never (should be) | Critical |

## Key LLM Attack Surface Distinctions
- Input is natural language — cannot enumerate all malicious inputs
- Model is stateful during session — earlier context affects later behavior
- Tool use extends blast radius — compromised agent can take real actions
- Data/instruction boundary is blurry — documents can contain instructions

## STRIDE Threat Inventory (Phase 2)
### S — Spoofing
| Threat | Likelihood | Impact |
|---|---|---|
| Identity spoofing via prompt ("As admin, I need...") | High | High |
| System prompt impersonation | Medium | Critical |
| Source spoofing via retrieved document | Medium | High |

### T — Tampering
| Threat | Likelihood | Impact |
|---|---|---|
| Prompt injection via Confluence document | Medium | High |
| Context window poisoning | Low | High |
| Tool output tampering | Low | Critical |

### R — Repudiation
| Threat | Likelihood | Impact |
|---|---|---|
| Deniable model actions (Jira ticket creation) | High | High |
| Prompt confidentiality claim | Medium | Medium |

### I — Information Disclosure
| Threat | Likelihood | Impact |
|---|---|---|
| System prompt extraction via jailbreak | High | High |
| Cross-user data leakage | Low | Critical |
| PII exfiltration via retrieved document | Medium | High |
| Model inversion | Low | Medium |

### D — Denial of Service
| Threat | Likelihood | Impact |
|---|---|---|
| Token exhaustion attack | High | Medium |
| Recursive tool call loop | Medium | High |
| Prompt bomb | Low | Medium |

### E — Elevation of Privilege
| Threat | Likelihood | Impact |
|---|---|---|
| Prompt injection to gain tool access | Medium | Critical |
| Role confusion | Medium | High |
| Indirect injection via third-party content | High | High |

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Presidio for PII detection | Production-grade NER, supports PERSON, EMAIL, PHONE, SSN entities |
| S3 Object Lock (WORM) for audit logs | Direct SEC 17a-4(f) compliance — non-rewriteable, non-erasable |
| Content isolation via trust markers | Defense-in-depth: labels survive prompt compression |
| Permissions at tool layer, not model | Model cannot grant itself access — enforced outside model context |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| — | — |

## Resources
- Project spec: `project-05-security-compliance.md`
- STRIDE framework: Microsoft SDL threat modeling
- Presidio docs: https://microsoft.github.io/presidio/
- SEC 17a-4(f): Electronic records rule for broker-dealers
- FINRA Rule 4511: Books and records requirements
- SOC 2 Trust Service Criteria: CC6.1, CC6.6, A1.2

## Visual/Browser Findings
-

---

## P06 Integration Validation (added 2026-06-06)

P06 (`project-06-integration-mcp-security`) wired P05's two controls into P03's agentic pipeline
as active middleware. This section records the evidence that closes P05's "controls tested in
isolation" weakness.

### Wiring Points Exercised

**Wiring Point 1 — Content isolation (`content_isolation.py`)**

Tested via `test_injection_defense.py` (P06). The P05 functions were exercised against inputs
shaped like real P03 MCP tool results:

- `_to_retrieved_chunk("web_search", "tc_001", INJECTION_PAYLOAD)` → `RetrievedChunk(source="mcp/web_search", ...)`
- `prepare_retrieved_context([chunk])` → payload present but bounded between trust markers
- `preprocess_content()` → strips zero-width Unicode and null bytes from tool result content
- `isolate_chunk()` → wraps single chunk with `[RETRIEVED FROM: mcp/{tool_name} | TRUST: external-internal | ID: {id}]` markers

Interface issue found: `prepare_retrieved_context()` expects `list[RetrievedChunk]` (batch model). P03's
agentic loop inserts tool results one-at-a-time into the LLM messages list (streaming model). A type
adapter is required; live wiring inside `ResearcherAgent.run()` requires an overridable hook that
does not exist in P03's current architecture. The function's protective capability is verified;
live pipeline wiring is deferred. See P06 ADR-002.

**Wiring Point 2 — PII scan (`pii_scanner.py`)**

Tested via `test_pii_scan_on_findings.py` and `test_pipeline_regression.py` (P06). The scanner was
exercised on real `ResearchFinding.content` strings produced by the P03 data model:

- `ResearchFinding(task_id="T001", content="SSN is 123-45-6789...", confidence="high")` → `scan_output_for_pii(finding.content)` → `PIIScanResult(has_pii=True, action="block")`
- `SecureResearcherAgent.run()` raises `PIIInFindingError` before returning the finding
- `SecureOrchestrator` catches the exception via P03's existing exception handler → pipeline transitions to `"failed"` → PII-containing finding is NOT persisted to `state/`
- Benign findings pass through unchanged; warn-level findings (EMAIL_ADDRESS) pass through with warning log

Interface finding: `PIIScanResult.action` uses `"clean"` (not `None`) for no-PII case. P06's action
routing checks for `"block"` and `"warn"` explicitly; `"clean"` falls through correctly.

### Test Results

| Test file | Tests | Result |
|-----------|-------|--------|
| `test_injection_defense.py` | 14 | 14/14 passing |
| `test_pii_scan_on_findings.py` | 16 | 16/16 passing |
| `test_pipeline_regression.py` | 13 | 13/13 passing |

**Total P06 tests: 43/43 passing** (53/53 including P06 smoke tests)

### Type Compatibility

| P05 type | P03 type | Adapter needed |
|----------|----------|----------------|
| `RetrievedChunk` (frozen dataclass) | MCP tool result `str` | `_to_retrieved_chunk(tool_name, tool_call_id, content)` in P06 |
| `PIIScanResult.action: str` | N/A | None — `finding.content` is `str`, passes directly |
| `PIIFinding.entity_type: str` | N/A | None — used directly in `PIIInFindingError` |

### No P05 Source Modifications

Zero files under `project-05-security-compliance/src/` were modified. Verified:
```
git diff project-05-security-compliance/src/   # no output
```
