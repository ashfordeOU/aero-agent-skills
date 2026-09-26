#!/usr/bin/env bash
# Run every ops/automation test suite as one gate.
#
# Extracted from an inline Makefile recipe on 2026-09-19, for two reasons the
# publish found the hard way:
#
#   1. The inline recipe had no entry in the negative-control battery, so
#      `make negative-controls` reported "NO CONTROL" and the public CI's
#      attest workflow failed -- while `make validate` and `make attest` were
#      both green locally. A gate nothing can prove red is not a gate.
#   2. It counted the suites it ran but never asserted how many there should
#      be. "Every suite passed" is trivially true of a set you have emptied,
#      so deleting eight of the nine left the gate green.
#
# Contract:
#   exit 0  every suite in DIR passed AND at least MIN suites were found
#   exit 1  at least one suite failed
#   exit 2  fewer than MIN suites found -- the set shrank, or the glob missed
#
# The floor is a floor, not a manifest: adding a suite needs no edit here,
# removing one does. It cannot catch an add and a delete in the same commit;
# pinning exact filenames would, at the cost of an edit on every addition.
# The floor is the proportionate half of that trade, and the reason is here
# so the next reader does not mistake it for an oversight.
set -uo pipefail

DIR="ops/automation"
MIN=11

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="${2:?--dir needs a value}"; shift 2 ;;
    --min) MIN="${2:?--min needs a value}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done

shopt -s nullglob
suites=( "$DIR"/test_*.py )
shopt -u nullglob

n=${#suites[@]}
if [ "$n" -lt "$MIN" ]; then
  echo "FAIL release-machinery: found $n suite(s) in $DIR, expected at least $MIN." >&2
  echo "  A shrinking set is not a passing gate. If a suite was retired on" >&2
  echo "  purpose, lower --min in the Makefile in the same commit." >&2
  exit 2
fi

fail=0
for t in "${suites[@]}"; do
  # unittest writes its OK/FAIL summary to STDERR, so both streams are
  # discarded and the exit code is the verdict.
  if ! python3 "$t" >/dev/null 2>&1; then
    echo "FAIL release-machinery: $t" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  exit 1
fi

echo "PASS release-machinery: $n suite(s) green"
