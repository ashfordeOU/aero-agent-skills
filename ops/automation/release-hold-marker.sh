#!/usr/bin/env bash
# release-hold-marker.sh — mirror the operator release HOLD into an export tree.
#
# Why (2026-09-11, relay tick): doctrine section 5 (ops/ecss-program/
# OPERATIONS.md) says the stop switch ~/.hermes/state/aero-release-HOLD
# "pauses all auto-cuts", but only release-manager.py --auto-cut ever read it.
# The PRIMARY release path is push -> publish-public -> release-on-milestone.yml
# running on the PUBLIC repo, and a GitHub workflow cannot see host-local
# state — so a held milestone still auto-cut on the next content push.
#
# Measured 2026-09-11: the dev tree sat at 800 leaves (166ddf66) while the
# public repo sat at 784 with no v1.7.0 tag and no v1.7.0 Release, and the
# switch was SET from 11:59Z. The cut that did fire (v1.7.0, 13:02:57Z) came
# from the 30m belt-and-braces cron -> release-manager.py --auto-cut, the ONE
# reader of the switch. The push-triggered workflow never consulted it and
# still would not, so "pauses all auto-cuts" held on one of the two cut paths
# only. This marker closes that half.
#
# Fix shape (same class as VEDA-0026 "policy was not a gate"): the publish
# path carries the switch WITH the export it is about to push, and the
# workflow refuses to cut while that marker is present. The host HOLD file
# stays the single source of truth and is NEVER written here (founder-owned
# switch); when it is removed, the next publish exports no marker and the
# automatic chain resumes on its own.
#
# Contract: exit 0 always — an absent HOLD is the normal open state, not an
# error. Usage: release-hold-marker.sh <export-tree>
set -uo pipefail

HOLD_FILE="${AERO_RELEASE_HOLD_FILE:-$HOME/.hermes/state/aero-release-HOLD}"
MARKER_NAME=".release-hold"
TREE="${1:-}"

if [ -z "$TREE" ]; then
  echo "usage: release-hold-marker.sh <export-tree>" >&2
  exit 2
fi
if [ ! -d "$TREE" ]; then
  echo "release-hold-marker: no such tree: $TREE" >&2
  exit 2
fi

MARKER="$TREE/$MARKER_NAME"
if [ -f "$HOLD_FILE" ]; then
  # Deliberately generic text: the export is pushed to a PUBLIC repo and the
  # publish path's machine-path tripwire fails the whole run on a host-local
  # absolute path, so the switch's own note must never be copied verbatim.
  {
    echo "release HOLD active — the automatic milestone cut is suppressed."
    echo "This marker is written by the publish path from the operator stop"
    echo "switch and disappears by itself when that switch is cleared."
  } > "$MARKER"
  echo "release-hold-marker: HOLD present — marker written to $MARKER_NAME"
else
  rm -f "$MARKER"
  echo "release-hold-marker: no HOLD — marker absent"
fi
exit 0
