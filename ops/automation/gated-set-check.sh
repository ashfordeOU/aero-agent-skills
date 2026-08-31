#!/usr/bin/env bash
# gated-set-check.sh — enumeration-completeness guard (P3.5 rework R3,
# Content Writer rec #2). Scans the three enumeration docs for numeric
# gated-set / map-coverage COUNT claims and verifies each against the LIVE
# standards-map.yaml (repo ROOT — the canonical map; there is no
# ops/automation/standards-map.yaml). Exit 0 = every count claim matches
# canonical; exit 1 = drift (file, line, claimed, expected).
#
# What this guard catches (the re-grader's root cause, verbatim: "the guard
# greps NUMBER patterns only, so a doc claiming 'map covers 9 standards'
# passes while the map covers 16"):
#   R1  '<N> gated standards' / 'gated set of <N> standards'      -> N == gated count (10)
#   R2  '<covers|maps|spans> <N> standards'                       -> N == map total (16)
#   R3  'all <N> of the gated standards'                          -> N == gated count (10)
# Digit and word forms (five..sixteen) both verified.
#
# Scope decision (documented, R3 rework): the guard verifies COUNT CLAIMS.
# Pure name-list drift ("Gated standards (DO-178C, ...)" listing 5 names
# without a number) is the Content Writer fix track — the live docs still
# carry those lists at HEAD, so gating them here would fail G8 and the task
# forbids editing copy (Content Writer lane). The guard makes the count-claim
# class fail CI and prevents the 'map covers 9 standards' regression; the
# name-list fix is tracked by Content Writer.
#
# Usage: bash ops/automation/gated-set-check.sh [root_dir]
#   (optional root_dir override for fixture testing; default = repo root.
#    standards-map.yaml is ALWAYS read from the real repo root so fixtures
#    verify planted claims against canonical truth.)
set -uo pipefail
auto_dir="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$auto_dir/gated_set_check.py" "$@"
