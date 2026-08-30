#!/usr/bin/env bash
# Gate 4 (STUB): no-verbatim RTCA/SAE/IAQG grep (copyright control).
# Policy: research/briefs/06-legal-export-control.md section 5.2 and 8.3.
# Full contract: docs/harness-contract.md. Extended scan lands 2026-09-04.
# Today: scan skills/ for verbatim-text markers (copyright/DRM/watermark
# boilerplate from proprietary standards). Exit 0 when nothing to scan or
# zero matches.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
scan_dir="$repo_root/skills"

if [ ! -d "$scan_dir" ]; then
  echo "PASS gate4-no-verbatim (STUB): no skills/ dir; nothing to scan"
  exit 0
fi

patterns=(
  'Copyright.*RTCA'
  'Copyright.*SAE'
  'Copyright.*IAQG'
  'RTCA proprietary'
  'PROPRIETARY AND CONFIDENTIAL'
  'single-user license'
  'standards\.rtca\.org'
)

hits=0
for pat in "${patterns[@]}"; do
  while IFS= read -r line; do
    echo "FAIL gate4-no-verbatim: $line" >&2
    hits=$((hits + 1))
  done < <(grep -rniE "$pat" "$scan_dir" 2>/dev/null || true)
done

if [ "$hits" -ne 0 ]; then
  echo "FAIL gate4-no-verbatim: ${hits} verbatim-text marker(s) found" >&2
  exit 1
fi
echo "PASS gate4-no-verbatim (STUB): 0 verbatim-text markers in skills/"
