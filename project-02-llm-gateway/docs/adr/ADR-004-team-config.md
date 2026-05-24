# ADR-004 — Team Configuration: YAML

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

The gateway needs team definitions: API keys, token budgets, allowed models, enforcement modes, routing strategies, and rate limits. This config changes rarely (when a team is added or budget changes) and is not user-generated data.

---

## Decision

**YAML file, loaded at startup.**

---

## Rationale

| Factor | YAML file | Environment variables | Database |
|--------|-----------|----------------------|----------|
| Multi-team support | Natural (list structure) | Awkward (key namespacing) | Yes |
| Readable by humans | Yes | Passable | Requires tooling |
| Version-controllable | Yes (git) | Partial (.env files) | No |
| Hot reload | Restart required | Restart required | Yes |
| Secrets management | Needs care (API keys in file) | Good fit | Overkill |
| Setup complexity | None | None | Requires migration |

YAML is the right tradeoff for a POC where team config is structural (belongs in version control) and runtime mutability is not required.

### Secrets concern

API keys in YAML are a concern for production. For POC: acceptable. Mitigation: YAML values support env var interpolation pattern (`${CE_API_KEY}`) so keys can be injected at runtime without being hardcoded in the file.

### Hot reload not required

Team definitions don't change frequently. Restart-to-reload is acceptable for POC. If hot reload becomes needed, a file watcher + config reload endpoint is a straightforward addition.

---

## Schema

See `gateway.yaml` in project root (created in Phase 1). Full schema documented in [DESIGN-001](../design/DESIGN-001-architecture.md#5-configuration-schema).

---

## Consequences

- Config file must be excluded from version control if it contains real API keys (`.gitignore`)
- Template config (`gateway.yaml.example`) committed with placeholder values
- Config loaded once at startup; changes require restart
- YAML parsing via `PyYAML` or `ruamel.yaml`

---

## Alternatives Not Chosen

- **Environment variables only**: works for single-team but becomes unmanageable with 5+ teams and per-team routing config
- **Database (SQLite/Postgres)**: requires migration tooling and UI or CLI to manage; overkill for config that changes rarely
- **JSON**: structurally equivalent to YAML; YAML preferred for comments and multi-line string readability
- **TOML**: valid alternative; YAML chosen for wider familiarity in infrastructure contexts
