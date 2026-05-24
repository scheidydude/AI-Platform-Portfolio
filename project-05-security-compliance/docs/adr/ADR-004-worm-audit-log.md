# ADR-004: S3 Object Lock (WORM) for Immutable Audit Logs

**Date:** 2026-05-23  
**Status:** Accepted  
**Deciders:** David Scheiderman  
**Project:** Project 05 — Enterprise Security & Compliance

---

## Context

FR-3 requires that every model interaction and tool call be logged immutably for compliance with SEC Rule 17a-4(f) and FINRA Rule 4511. These regulations specifically require:

> Records must be preserved in a **non-rewriteable, non-erasable** format and be readily accessible for examination.

SEC 17a-4(f) was written for electronic records in broker-dealer environments and predates cloud storage. The SEC has issued guidance (2003 letter) clarifying that WORM-compliant cloud storage satisfies the regulation provided:
1. Records cannot be altered or deleted before the retention period expires
2. An audit trail of access exists
3. Records are readily accessible (retrievable within a reasonable time)
4. A third party (or internal compliance) can verify integrity

FINRA Rule 4511 requires retention of business communications for a minimum of 3 years (6 years for certain record types). AI assistant interactions that constitute business communications fall under this rule.

We need a storage solution that:
- Enforces non-rewriteable, non-erasable storage at the infrastructure level (not just application level)
- Supports per-record or per-prefix retention periods (6 years)
- Is auditable — the storage system itself keeps access logs
- Is queryable — compliance team can retrieve records by user, session, or date
- Is available on AWS (infrastructure constraint)

---

## Decision

Use **Amazon S3 with Object Lock in Compliance mode** as the immutable audit log store.

**Configuration:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| Object Lock mode | Compliance | Cannot be overridden even by root account — satisfies 17a-4(f) |
| Retention period | 6 years (2190 days) | FINRA 4511 maximum |
| Storage class | S3 Intelligent-Tiering | Cost-optimized; older logs move to cheaper tiers automatically |
| Access logging | S3 Server Access Logging enabled | Audit trail of who accessed which records |
| Encryption | SSE-KMS with customer-managed key | Records encrypted at rest; key access logged in CloudTrail |

**Log format:** Newline-delimited JSON (one record per line), written as individual objects per session. Prefix structure: `logs/{year}/{month}/{day}/{session_id}.jsonl`

**Log record structure:**
```json
{
  "schema_version": "1.0",
  "session_id": "uuid",
  "user_id": "ssoid",
  "timestamp_utc": "ISO8601",
  "event_type": "user_message | tool_call | model_output | pii_block | permission_deny",
  "payload": { ... }
}
```

**Write path:** Async write from LLM orchestrator → SQS → Lambda writer → S3 Object Lock. Failure in write path triggers CloudWatch alarm; does not block user response (NFR-3).

---

## Consequences

**Positive:**
- S3 Object Lock Compliance mode satisfies SEC 17a-4(f) non-rewriteable requirement at infrastructure level — no application-level enforcement needed
- AWS manages WORM enforcement; we cannot accidentally bypass it
- S3 Server Access Logging provides audit trail of who accessed records
- JSONL format is queryable via Athena without data movement
- Lifecycle policies handle retention automatically

**Negative:**
- Compliance mode Object Lock is truly irreversible — accidental writes with incorrect retention lock cannot be unlocked
- 6-year retention at scale can become significant storage cost (mitigated by Intelligent-Tiering)
- Async write path introduces a window where a system failure could lose a log record between orchestrator and S3 (mitigated by SQS durability — messages survive Lambda failures)

**Mitigations:**
- Test Object Lock behavior in a non-production bucket before enabling on production
- SQS dead-letter queue captures failed log writes; alert on DLQ depth
- Log schema versioned (schema_version field) to allow format evolution without breaking existing records

---

## Compliance Verification

| Regulation | Requirement | How This Satisfies It |
|------------|-------------|----------------------|
| SEC 17a-4(f)(2)(ii) | Non-rewriteable, non-erasable | S3 Object Lock Compliance mode — cannot be deleted or modified before retention expiry, even by AWS root |
| SEC 17a-4(f)(3)(i) | Readily accessible for examination | S3 + Athena; records retrievable by session ID, user, or date range |
| SEC 17a-4(f)(2)(iii) | Audit trail of access | S3 Server Access Logging + CloudTrail KMS key access |
| FINRA 4511(b) | Retain for 3 years (6 for certain records) | 6-year Object Lock retention on all records |

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| CloudWatch Logs with retention | CloudWatch does not provide WORM guarantee — logs can be deleted |
| DynamoDB | No Object Lock equivalent; point-in-time recovery is not WORM |
| Custom WORM implementation in RDS | Would need to prove WORM compliance to auditors; S3 Object Lock is pre-certified |
| AWS Glacier Vault Lock | Satisfies WORM but retrieval latency (hours) does not meet "readily accessible" requirement |

---

*Related: [SRS-001 FR-3, NFR-1](../srs/SRS-001.md), [DESIGN-001 §2.1](../design/DESIGN-001.md)*
