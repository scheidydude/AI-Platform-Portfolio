# ADR-002 — Additive `sandboxed_execution` Mode, Reusing Orchid's Task/Result Schema

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

Orchid's `TesterAgent` currently supports only a `verify_syntax_only` mode. The PM Dashboard and ccview already consume Orchid's existing task/result schema. P07 needs to add real code execution without breaking either.

## Decision

`sandboxed_execution` is added as a new mode on `TesterAgent`, alongside `verify_syntax_only`, not as a replacement. The execution API's `{stdout, stderr, exit_code, duration_ms}` response is mapped into Orchid's existing task/result schema — no parallel result format is introduced.

## Rationale

- `verify_syntax_only` has existing callers; removing or altering it is an unforced regression.
- The PM Dashboard's task metrics display already renders Orchid's result schema. A second schema would require dashboard changes to consume it, which is out of scope and unnecessary.
- Keeping the schema shared means anything built for `sandboxed_execution` (P07) is automatically compatible with P08's Firecracker backend later, since both map onto the same schema.

## Consequences

- The execution API's response fields must be expressible within Orchid's existing schema; if a new field is genuinely required (e.g. syscall log reference for FR-5), it must be added as an optional/additive field to that schema, not a new format.
- `TesterAgent`'s existing tests and `verify_syntax_only` behavior must be re-verified unchanged after this change lands.
