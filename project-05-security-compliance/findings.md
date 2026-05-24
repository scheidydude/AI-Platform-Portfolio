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
