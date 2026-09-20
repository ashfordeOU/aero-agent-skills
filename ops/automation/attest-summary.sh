#!/usr/bin/env bash
# The attest summary line is the sentence people quote. It must not describe a
# gate that verified nothing as "clean".
#
# brief-audit already says so itself, plainly:
#
#   EMPTY brief-audit: denominator 0 — 16 file(s) scanned, 26 figure
#   candidate(s) seen, NONE of them resolvable against numbers.yaml. This run
#   verified NOTHING.
#
# ...and then exits 0, and the summary counted it among "7/7 gates exited
# clean". The old line even carried the warning "read each gate verdict line;
# EMPTY is not a PASS" — an instruction to a human, enforced by nothing. So
# the count is now split: gates that verified something, and gates that ran
# clean while reading nothing.
#
# This does NOT fail the build. An empty denominator is a coverage fact, not a
# defect: brief-audit resolves external market claims, and the briefs in this
# tree currently hold none that numbers.yaml can resolve. Our own corpus
# figures are covered by figure-audit (13 denominators) and competitor star
# counts by number-snapshot. Making it fatal would stop the publish chain over
# a gate with an empty scope. Making it invisible is what we are fixing.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2
total="${1:-0}"

empty=0
notes=""

# brief-audit is the only gate that can report an EMPTY denominator. It is
# offline and reads 16 files, so re-deriving the verdict here is cheap and
# deterministic.
if ops/automation/brief-audit.sh 2>&1 | grep -q '^EMPTY brief-audit:'; then
  empty=$((empty + 1))
  notes="brief-audit resolved 0 of its figure candidates"
fi

verified=$((total - empty))

if [ "$empty" -eq 0 ]; then
  echo "Aero Agent Skills attest: ${total}/${total} gates exited clean, none reporting an empty denominator"
  exit 0
fi

echo "Aero Agent Skills attest: ${verified}/${total} gates verified something; ${empty} exited clean while reading nothing (${notes})"
echo "  A green attest does NOT cover what an empty gate did not read. Run 'make attest-strict' to make an empty denominator fail."
exit 0
