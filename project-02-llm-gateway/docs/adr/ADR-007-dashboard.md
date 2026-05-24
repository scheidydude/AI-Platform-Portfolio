# ADR-007 — Cost Dashboard: Embedded HTML + Vanilla JS

**Status:** Accepted  
**Date:** 2026-05-23  
**Deciders:** David Scheiderman

---

## Context

The project requires a cost dashboard showing: monthly spend by team, daily trend, model distribution, and teams approaching quota. This must be served by the gateway itself (no external deployment).

---

## Decision

**Single-page HTML/JS app embedded in a FastAPI route. Data served via existing admin JSON endpoints. No build step, no framework, no separate frontend server.**

---

## Rationale

| Approach | Complexity | Deploy | Live data | Career signal |
|----------|-----------|--------|-----------|---------------|
| Embedded HTML (this) | Low | Zero | Yes (API calls) | Shows fullstack judgment |
| Grafana dashboard | Medium | Separate container | Yes (Prometheus) | Shows infra tooling |
| Static files + build | High | CI/CD needed | Yes | Overkill for POC |
| Server-rendered Jinja2 | Low-Medium | Zero | Yes | Less reusable |

Embedded HTML eliminates the static file serving question and keeps the gateway self-contained. The dashboard is a Python string constant — no assets to deploy, no build step, no web framework.

The data layer uses the same admin JSON endpoints that exist for programmatic use. This validates those endpoints actually work end-to-end, rather than having dashboard-specific DB queries.

### Security model

The dashboard HTML is served unauthenticated — it's just markup and JS. All data fetches require the admin key sent as `X-Admin-Key` header. The key is stored in `sessionStorage` (not localStorage) so it doesn't persist across browser sessions. This is appropriate for an internal admin tool.

### Chart library choice

Chart.js from CDN. Reasons:
- Well-known, used in production dashboards
- No build step (UMD bundle via CDN)
- Sufficient for bar/line charts the dashboard needs
- Alternative (D3.js): far more powerful but verbose for simple charts

CDN dependency is a POC tradeoff — production would bundle Chart.js locally.

---

## Consequences

- Dashboard lives at `/dashboard` — no auth, but all data requires admin key
- Chart.js loaded from CDN (`cdn.jsdelivr.net`) — requires internet access to render charts
- Auto-refreshes every 30 seconds
- A `/admin/daily` endpoint was added specifically to support the daily trend chart

---

## Alternatives Not Chosen

- **Grafana**: right for production; requires separate deployment and Prometheus scraping configured
- **Streamlit/Dash**: Python-native dashboards; adds heavy dependencies (pandas, etc.) not otherwise needed
- **Server-side HTML (Jinja2)**: adds templating dependency; less reusable than JSON API + JS
