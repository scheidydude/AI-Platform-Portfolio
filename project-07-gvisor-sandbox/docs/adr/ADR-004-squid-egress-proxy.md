# ADR-004 — Squid Forward-Proxy Sidecar for Egress Allowlisting

**Status:** Accepted
**Date:** 2026-08-07
**Deciders:** David Scheiderman

---

## Context

SRS-001 FR-3 requires sandboxed executions to have no network access by default, with an explicit domain allowlist available on request. The original plan assumed this would route through "the existing Traefik/proxy configuration." Phase 0 recon (see `findings.md`) found that assumption wrong: the host's one live Traefik instance is purely an ingress reverse proxy (external HTTPS → internal services via `Host()` rules) with no forward-proxy or egress capability at all, and no forward-proxy tooling (squid/tinyproxy/etc.) exists on the host.

The allowlist half of FR-3 therefore requires genuinely new infrastructure, not hardening of something that already exists — a different situation from Phase 2, where `ContainerRunner` already did the relevant work and just needed flags added.

## Decision

Build a dedicated Squid forward-proxy sidecar container for the egress-allowlist path:

- Default-deny sandboxes (no allowlist configured) run with `--network none`, unchanged from the original plan — this needs no new infrastructure.
- Allowlisted sandboxes join a Docker `--internal` network (no default route to the outside world) that only the Squid sidecar also joins (in addition to a normal external-facing network). The sandbox reaches the internet only by routing through Squid via `HTTP_PROXY`/`HTTPS_PROXY`.
- Squid's ACL (`acl allowed_dst_domains dstdomain ...`) enforces the actual domain allowlist; `http_access deny all` as the default-deny fallback inside Squid itself, plus the standard `Safe_ports`/`SSL_ports`/`CONNECT` ACLs to prevent port-scanning or protocol-smuggling through the proxy.

## Alternatives Considered

- **DNS-based filtering + IP restriction.** Rejected — requires standing up a custom DNS resolver as a second new piece of infrastructure, and still needs an IP-level enforcement layer to prevent bypassing the resolver with a hardcoded IP, making it strictly more moving parts for the same guarantee a proxy sidecar gives directly.
- **Custom Docker bridge + iptables/nftables rules keyed to destination IP.** Rejected — domain-based allowlisting (the actual requirement) doesn't map cleanly onto IP-based firewall rules, since allowlisted domains served by CDNs or load balancers resolve to IPs that rotate. A proxy that inspects the `Host`/SNI at the application layer is the correct primitive for a domain allowlist; a firewall rule is the wrong layer for it.

## Consequences

- New infrastructure to build and demo, not just config wiring — this is a real addition to the project's scope for Phase 3, not a one-line flag like Phase 2.
- The sandbox's egress path when allowlisted is: sandbox → internal-only Docker network → Squid (dual-homed) → internet. Squid is a single point of failure for allowlisted egress; acceptable for a portfolio demo, would need HA consideration in production.
- HTTPS traffic through Squid is a CONNECT tunnel — Squid can enforce the domain allowlist via SNI/`dstdomain` on the CONNECT target without needing to MITM/decrypt TLS, so allowlisted sites' certificates remain intact from the sandboxed process's perspective.
- This ADR and FR-3 apply only to sandboxed *task* execution via `ContainerRunner`. It has no relationship to Orchid's own outbound traffic (e.g. LLM API calls), which is unaffected.
