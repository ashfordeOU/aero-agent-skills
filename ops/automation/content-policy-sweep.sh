#!/usr/bin/env bash
# AeroSkills content-policy sweep (attestation part 3).
# Scans publishable content for red-flag terms per research/briefs/
# 06-legal-export-control.md s8.3.6 / s8.3.9 (content policy) + task list:
#   - ITAR/EAR/export compliance CLAIMS ("ITAR-compliant", "ITAR certified",
#     "EAR-compliant", "export-compliant") — mis-marking public content is
#     itself a compliance failure (06 s8.3.9). Bare mentions ("not
#     ITAR-controlled") and the README compliance banner (06 s8.4) are allowed.
#   - unapproved certification claims ("FAA-certified", "EASA-certified",
#     "DO-178C-certified", "certified for flight")
#   - classified markings (CLASSIFIED, SECRET//NOFORN, NOFORN, CONTROLLED
#     UNCLASSIFIED, CUI)
#   - part-number patterns (P/N <digits>, NSN, CAGE)
#   - specific military platform parameters (F-35/F-22/JSF/AIM-9 etc.)
# Scan roots: README.md, marketing/, docs/, development/builds/, skills/,
# support/ (publishable content). research/ briefs are internal evidence and
# legitimately discuss the policy terms — exempt by design.
#
# SCOPE DECISION (P2.1 rework, 2026-08-31): repo_root is TWO levels up from
# ops/automation (../..), i.e. the repository root — NOT three (../../..),
# which resolved to $HOME and made this sweep vacuous (skills/ never scanned).
# The corrected sweep genuinely scans README.md + marketing/ + docs/ +
# development/builds/ + skills/ + support/.
#
# Meta-doc exemption: documents whose purpose is to DEFINE this sweep or the
# policy itself necessarily quote the red-flag terms (e.g. the attestation
# gates design spec lists "CLASSIFIED/SECRET//NOFORN" as the pattern being
# swept). Those are definitional quotes with clear context, exempted below by
# explicit relative path. Buyer-facing content (README, marketing, skills,
# support) is NEVER exempt: any hit there fails the gate.
# Exit 0 clean; exit 1 listing file:line for each hit. Wired into CI.
set -uo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

# Explicit meta-doc exemptions (definitional quotes of policy terms).
# Keep this list minimal and auditable: every entry states WHY in a comment.
meta_doc_exempt=(
  "docs/superpowers/specs/2026-08-31-attestation-gates-design.md" # defines the sweep pattern list itself
)

if [ "$#" -gt 0 ]; then
  roots=("$@")
else
  roots=("$repo_root/README.md" "$repo_root/marketing" "$repo_root/docs"
         "$repo_root/development/builds" "$repo_root/skills" "$repo_root/support")
fi

patterns=(
  'ITAR[- ]?compliant'
  'ITAR[- ]?certif'
  'EAR[- ]?compliant'
  'export[- ]?compliant'
  'FAA[- ]?certified'
  'EASA[- ]?certified'
  'DO-178C[- ]?certified'
  'certified for flight'
  'CLASSIFIED|SECRET//NOFORN|NOFORN|CONTROLLED UNCLASSIFIED|\bCUI\b'
  'P/N[ :]?[0-9A-Z]{4,}'
  '\bNSN[ :]?[0-9]{4}'
  '\bCAGE[ :]?[A-Z0-9]{5}'
  '\bF-35\b|\bF-22\b|\bJSF\b|\bAIM-9\b|warhead fuzing|missile guidance|stealth design'
)

hits=0
# skip <line> — drop grep lines from exempt meta-doc paths (definitional
# quotes of the policy terms, recorded in the header). Matches the relative
# path wherever it appears in grep's "<abs-or-rel-path>:<line>:" prefix.
skip_exempt() {
  local line="$1" ex
  for ex in "${meta_doc_exempt[@]}"; do
    case "$line" in
      *"$ex:"*) return 1 ;;
    esac
  done
  return 0
}
for pat in "${patterns[@]}"; do
  while IFS= read -r line; do
    skip_exempt "$line" || continue
    echo "FAIL content-policy-sweep: $line" >&2
    hits=$((hits + 1))
  done < <(grep -rniIE -- "$pat" "${roots[@]}" 2>/dev/null || true)
done

if [ "$hits" -ne 0 ]; then
  echo "FAIL content-policy-sweep: ${hits} red-flag hit(s) in publishable content (brief 06 s8.3.6/8.3.9)" >&2
  exit 1
fi
echo "PASS content-policy-sweep: 0 red-flag hits in publishable content"
