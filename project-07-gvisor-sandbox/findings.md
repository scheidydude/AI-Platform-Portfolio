# P07 Findings

Research notes and decisions, accumulated as the project progresses.

## 2026-08-07 — Phase 0 recon (partial, host state)

Ran directly on the NucBox (Claude Code CLI has no `sudo` — privileged steps below must be run by David manually).

- **Host:** `dave-NucBox-EVO-X2`, Ubuntu 25.10 (Questing Quokka), kernel `6.19.0-061900rc8-generic` (mainline RC build, not a stock Ubuntu kernel — worth re-checking `runsc` compatibility against this specific kernel, not just "Ubuntu 25.10" in general).
- **Docker:** 29.6.1 installed and running.
- **`runsc`:** not installed (`command not found`). Needs install — see below.
- **KVM:** `/dev/kvm` present, `kvm_amd` + `kvm` modules loaded. Good sign for P08 (Firecracker) as well — no separate KVM enablement work needed.
- **Docker group:** `dave` is a member of the `docker` group (`getent group docker` → `docker:x:980:dave`), but the current shell session predates that membership — `docker ps` fails with a permission error until the group takes effect. Not a real blocker: fixable with `newgrp docker`, a new shell, or re-login. If it's still failing when Phase 1 work starts, check this first before assuming a real permissions problem.

### Needed: install `runsc` (run manually, requires sudo)

Official gVisor apt install for Ubuntu/Debian:

```bash
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
sudo apt-get update
sudo apt-get install -y runsc
```

Then register it as a secondary Docker runtime (per ADR-001 — do not replace the default runtime):

```bash
sudo runsc install    # patches /etc/docker/daemon.json to add the runsc runtime entry
sudo systemctl restart docker
```

Verify:

```bash
runsc --version
docker run --rm --runtime=runsc hello-world
docker ps -a --filter runtime=runsc   # confirm no leftover containers after the test
```

After this is run, come back and I'll continue Phase 0 recon (`TesterAgent` audit, Traefik config location) and move into Phase 1 verification (syscall-interception test).

### Still open (Phase 0 checklist)

- [ ] `runsc` install (blocked — needs sudo, see above)
- [ ] Confirm `runsc` version/build compatible with kernel `6.19.0-061900rc8-generic` specifically
- [ ] Audit Orchid `TesterAgent` current modes and task/result schema shape — Orchid repo location on this host not yet confirmed
- [ ] Confirm Traefik config location for later allowlist wiring
- [ ] Supported `language` values + base image(s) for the execution API
- [ ] Default `timeout_s` / `memory_mb` values
- [ ] Sandbox container teardown/cleanup step
- [ ] `runsc` rollback plan (beyond "remove the daemon.json entry and restart Docker" — confirm that's sufficient)
