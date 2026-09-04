#!/usr/bin/env bash
# Aero Agent Skills content-policy sweep (attestation part 3).
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
  "docs/MAINTENANCE_AND_HANDOVER.md" # internal handover doc; quotes the red-flag terms to WARN builders against them (founder mandate 2026-09-04) — never shipped to buyers
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
# Base64-embedded assets (e.g. a raster <image> inlined into a generated
# SVG) are binary-as-text: at any real size their alphabet trivially
# produces false hits on P/N-, NSN-, CAGE-style patterns by pure chance —
# a 200+ char unbroken base64-alphabet run is never itself policy-relevant
# prose (that length rules out any real part number/marking living inside
# one). Elide such runs before pattern matching so the sweep still covers
# the surrounding markup/text, added 2026-09-02 after docs/social-card-dark.svg
# (a base64-embedded logo) tripped the part-number pattern.
#
# Elision happens ONCE per file into a scratch mirror (not once per
# pattern x file — that first cut spawned a sed+grep pair per pattern per
# candidate, ~13,000 subprocesses, and was too slow for the pre-push gate).
# The mirror preserves each file's full absolute path under $scratch, so
# after grep -r finds matches there, stripping the $scratch prefix restores
# exactly the original "<abs-path>:<line>:<content>" shape skip_exempt and
# the FAIL message expect — same multi-file-per-pattern grep speed as the
# original single-pass design.
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

# Text-vs-binary detection matches grep -I's own heuristic (a NUL byte
# anywhere marks a file binary) so this candidate list covers exactly what
# the original whole-directory `grep -rI` scanned — true binaries (.png,
# .pyc) are skipped the same way, nothing new is silently excluded.
while IFS= read -r f; do
  [ -f "$f" ] || continue
  mkdir -p "$scratch$(dirname "$f")"
  sed -E 's/[A-Za-z0-9+\/=]{200,}/[BASE64-DATA-ELIDED]/g' "$f" > "$scratch$f"
done < <(find "${roots[@]}" -type f -print0 2>/dev/null \
  | xargs -0 grep -IlZ . 2>/dev/null | tr '\0' '\n' || true)

for pat in "${patterns[@]}"; do
  while IFS= read -r scratch_line; do
    line="${scratch_line#"$scratch"}"
    skip_exempt "$line" || continue
    echo "FAIL content-policy-sweep: $line" >&2
    hits=$((hits + 1))
  done < <(grep -rniIE -- "$pat" "$scratch" 2>/dev/null || true)
done

if [ "$hits" -ne 0 ]; then
  echo "FAIL content-policy-sweep: ${hits} red-flag hit(s) in publishable content (brief 06 s8.3.6/8.3.9)" >&2
  exit 1
fi
echo "PASS content-policy-sweep: 0 red-flag hits in publishable content"
