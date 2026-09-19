#!/usr/bin/env bash
# Aero Agent Skills brief-audit gate (attestation part 2).
# Scans repo docs for quoted market numbers and resolves each against
# ops/automation/numbers.yaml (canonical register).
#
# Every run prints a denominator report first: roots configured, roots absent
# from the tree, files scanned, figure candidates seen, FIGURES CHECKED, and a
# reason for every candidate it could not check. Three verdicts, never two:
#   FAIL  <n> drift(s)                 exit 1
#   EMPTY denominator 0 - nothing was checked, so nothing was verified
#                                      exit 0, or exit 1 with --strict
#   PASS  <n> figure(s) resolved       exit 0
# EMPTY is deliberately NOT a PASS: a gate that resolved zero figures supports
# no claim, and printing the same word a 3,000-figure run prints would hand a
# reviewer credibility the run did not earn. It stays exit 0 by default because
# a tree that legitimately quotes no market figure is not defective; a pipeline
# that wants a zero denominator to block passes --strict.
#
# Usage: brief-audit.sh [--strict] [path...]
#        BRIEF_AUDIT_STRICT=1 brief-audit.sh      (same as --strict)
# Defaults when no path is given: research/ marketing/ development/ docs/ README.md
set -uo pipefail
auto_dir="$(cd "$(dirname "$0")" && pwd)"
if [ "${BRIEF_AUDIT_STRICT:-0}" = "1" ]; then
  exec python3 "$auto_dir/number_audit.py" --strict "$@"
fi
exec python3 "$auto_dir/number_audit.py" "$@"
