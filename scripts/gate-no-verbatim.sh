#!/usr/bin/env bash
# Gate 4 (REAL): no-verbatim, family-aware (copyright control).
# Policy: research/briefs/06-legal-export-control.md section 5.2
# (summarize-not-copy); full contract docs/harness-contract.md gate 4.
#
# Two runners, both deterministic and offline:
#
#   tools/verbatim_gate.py         publisher markers for EVERY standards
#                                  family in the corpus, plus a source-text
#                                  comparison for every family whose source
#                                  documents were available at index-build
#                                  time, plus a coverage line naming the
#                                  families that got neither. A family the
#                                  gate cannot check reports UNCHECKED; it
#                                  never reports PASS.
#   scripts/verbatim_table_scan.py objective-table blocks ('Table A-1' /
#                                  'A-1.1' runs), unchanged.
#
# Until 2026-09-19 this script was the whole gate: fifteen grep patterns
# naming RTCA, SAE, IAQG and EUROCAE. Those four publishers account for 216
# of the 3,021 leaves; the other 2,805 -- ECSS above all -- were scanned by
# patterns that could not match their sources, and the run still printed
# PASS. The patterns moved into tools/verbatim_gate.py unchanged; what is
# new is the rest of the families, the ECSS source-text check and the
# coverage line.
#
# Add --strict (or run `make no-verbatim-strict` if it is wired) to fail on
# an unchecked family instead of reporting it.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"

status=0

python3 "$repo_root/tools/verbatim_gate.py" "$@" || status=1

scans=()
for d in skills docs; do
  if [ -d "$repo_root/$d" ]; then
    scans+=("$repo_root/$d")
  fi
done
# Published content at the repo root is scanned too (P3.5 hygiene flag):
# README.md, STANDARDS.md, NOTICE are the same class of publishable
# surface as skills/ and docs/ and must stay marker-free.
for f in README.md STANDARDS.md NOTICE; do
  if [ -f "$repo_root/$f" ]; then
    scans+=("$repo_root/$f")
  fi
done

if [ "${#scans[@]}" -ne 0 ]; then
  python3 "$repo_root/scripts/verbatim_table_scan.py" "${scans[@]}" || status=1
fi

if [ "$status" -ne 0 ]; then
  echo "FAIL gate4-no-verbatim" >&2
  exit 1
fi
