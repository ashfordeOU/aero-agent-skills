#!/usr/bin/env bash
# Gate 4 (REAL): no-verbatim RTCA/SAE/IAQG grep (copyright control).
# Policy: research/briefs/06-legal-export-control.md section 5.2
# (summarize-not-copy); full contract docs/harness-contract.md gate 4.
# Scans published content (skills/ + docs/) for verbatim-text markers from
# proprietary standards (RTCA/SAE/IAQG boilerplate, DRM/license-restriction
# lines, watermark fragments) plus objective-table blocks (scripts/verbatim_table_scan.py).
# Zero matches required.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"

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

if [ "${#scans[@]}" -eq 0 ]; then
  echo "PASS gate4-no-verbatim: no skills/ or docs/ content to scan"
  exit 0
fi

patterns=(
  'Copyright.*RTCA,? ?(Inc|International|Europe)'
  'RTCA, Inc.*All Rights Reserved'
  'All [Rr]ights [Rr]eserved.*RTCA'
  'Copyright.*SAE International'
  'Copyright.*IAQG'
  'Copyright.*EUROCAE'
  'RTCA proprietary information'
  'Electronic License Agreement'
  'PROPRIETARY AND CONFIDENTIAL'
  'This document is licensed to'
  'not for redistribution'
  'standards\.rtca\.org'
  'sae\.org/standards/content'
  'single-user license'
  'DRM-protected'
)

hits=0
for pat in "${patterns[@]}"; do
  while IFS= read -r line; do
    echo "FAIL gate4-no-verbatim: $line" >&2
    hits=$((hits + 1))
  done < <(grep -rniE -- "$pat" "${scans[@]}" 2>/dev/null || true)
done

table_fail=0
if ! python3 "$repo_root/scripts/verbatim_table_scan.py" "${scans[@]}"; then
  table_fail=1
fi

if [ "$hits" -ne 0 ] || [ "$table_fail" -ne 0 ]; then
  echo "FAIL gate4-no-verbatim: ${hits} marker(s) + table blocks found" >&2
  exit 1
fi
echo "PASS gate4-no-verbatim: 0 markers in ${#scans[@]} scan root(s) (skills/, docs/, README.md, STANDARDS.md, NOTICE)"
