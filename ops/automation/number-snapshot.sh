#!/usr/bin/env bash
# Aero Agent Skills number snapshot gate (attestation part 1).
# Live: reads ops/automation/numbers.yaml (tracked + derived.largest), calls
# GitHub API via gh (authed arjun-0077) for each tracked repo, writes a
# timestamped snapshot to ops/automation/state/, exits 0 only when live stars
# are within expected range (else 1 with diff). API failure -> exit 2, no
# silent fallback.
# Offline: --offline re-checks the newest snapshot against the register;
# missing snapshot -> exit 1 (never silent drift).
# Usage: number-snapshot.sh [--live|--offline]
set -uo pipefail
auto_dir="$(cd "$(dirname "$0")" && pwd)"
mode="--offline"
[ "${1:-}" = "--live" ] && mode="--live"
exec python3 "$auto_dir/number_snapshot.py" "$mode"
