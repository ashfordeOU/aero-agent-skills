#!/usr/bin/env bash
# gate-verify-independence.sh - gate 6: verifier independence.
#
# Rule (founder 2026-09-10): the agent/process that VERIFIES an artifact
# must be independent of the one that GENERATED it. No bot grades its own
# output. Deterministic checkers (script/test/hash/count) always qualify;
# a same-model verifier does not.
#
# Scans the repo for claims ledgers and evidence bundles (model.json +
# gates.json) and fails on generator/verifier collisions, self-references,
# and same-LLM-family pairs. Applies to every leaf the ECSS program adds.
#
# Exit 0 = clean (or no artifacts yet), 1 = violation.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$REPO/scripts/verify-independence.py" "$REPO"
rc=$?
if [ "$rc" -eq 0 ]; then
  echo "gate 6 verify-independence: PASS"
else
  echo "gate 6 verify-independence: FAIL" >&2
fi
exit "$rc"
