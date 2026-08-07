#!/usr/bin/env bash
# P07 Phase 1 syscall-interception verification (FR-1).
# Requires: docker group membership active in this shell (or run via `sg docker -c`).
set -euo pipefail

PROBE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/probe_io_uring.py"
IMAGE="python:3.12-slim"

echo "### 1. Kernel identity: runc (default runtime) ###"
docker run --rm "$IMAGE" sh -c "uname -a && cat /proc/version"
echo

echo "### 2. Kernel identity: runsc (gVisor) ###"
docker run --rm --runtime=runsc "$IMAGE" sh -c "uname -a && cat /proc/version"
echo

echo "### 3. io_uring_setup: runc, Docker default seccomp ###"
docker run --rm -v "$PROBE":/probe.py "$IMAGE" python3 /probe.py
echo

echo "### 4. io_uring_setup: runc, seccomp unconfined (raw host kernel behavior) ###"
docker run --rm --security-opt seccomp=unconfined -v "$PROBE":/probe.py "$IMAGE" python3 /probe.py
echo

echo "### 5. io_uring_setup: runsc (gVisor sentry) ###"
docker run --rm --runtime=runsc -v "$PROBE":/probe.py "$IMAGE" python3 /probe.py
