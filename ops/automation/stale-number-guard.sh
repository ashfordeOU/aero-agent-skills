#!/usr/bin/env bash
# Stale-number guard (R2 rework, Market rec #2; ops track extended R3;
# scan roots extended R4).
# Scans LIVE corpus/skill/pack count claims that contradict the live
# repo state (102 tasks / 43 leaf skills / 9 installable packs; 50x20
# tree: 73 packs, 1,460 leaf skills, Wave 4 43 -> 540). Patterns:
#   '28/28'             P2.1-era Hit@1 count (live: 102/102)
#   '12 skills'         P2.1-era skill count, digit form (live: 43)
#   'twelve skills'     P2.1-era skill count, word form (live: forty-three)
#   'twenty-eight'      P2.1-era corpus count (live: one hundred two)
#   'five installable'  P3.6-era pack count (live: nine)
#   'five packs'        P3.6-era pack count, literal form (live: nine) [R3]
#   '12 verified'       P2.1-era skill count, 'verified' form (live: 43)
#   '12 aerospace ...'  P2.1-era skill count, marketing form (live: 43);
#                       narrowed R4 to '12 aerospace( engineering)? skills'
#                       so the tree's legit '12 aerospace disciplines'
#                       (12 families) is not a false positive
#   '3/3 corpus'        P2.1-era corpus-ratio claim, corpus context (live: 102/102) [R3]
#   '68 installable'    R1-era 50x20 pack count (live: 73) [R4]
#   '1,360'             R1-era 50x20 leaf-skill total (live: 1,460) [R4]
#   '27 skills'         P5.1-era leaf-skill count (live: 43) [R3 re-grade]
#   '27 aerospace'      P5.1-era leaf count, marketing form (live: 43)
#   '27 leaf skills'    P5.1-era leaf count, 'leaf' form (live: 43)
#   '9 packs'           P5.1-era family mislabel (live: 27 sub-domain
#                       packs / 9 family routers). Bare digit form only:
#                       'sub-domain packs' without the bare count is
#                       legit ('27 live sub-domain packs',
#                       '73 sub-domain packs'), and '9 pack routers'
#                       is the live router count - neither trips
#   '9 domain packs'    P5.1-era family mislabel, 'domain' form
#   '9 installable'     P5.1-era pack count, digit form (live docs say
#                       'nine installable domain packs' in words)
#   '36 SKILL.md'       P5.1-era SKILL.md total (live: 52)
# All seven new forms are digit-form on purpose: the live one-way
# vocabulary ('nine installable domain packs', '9 family routers',
# '9 disciplines', '9 families', '43 leaf skills', '52 SKILL.md',
# '102/102', '27 live sub-domain packs', '73 sub-domain packs',
# '1,460', '43 -> 540') shares the numbers but never the stale
# digit-phrase shapes, so word-boundary patterns separate them.
# Exemption (documented, R4): lines carrying the explicit qualifier
# 'planning target, not a shipped count' are NOT stale shipped claims.
# README.md's roadmap copy (Content Writer track) names the old
# 68-pack/1,360-skill plan as a planning target (qualified), so the
# guard exempts exactly that qualifier; ANY unqualified '68 installable'
# or '1,360' claim still trips. The exemption is line-scoped: the
# qualifier must sit on the same line as the number (as README states
# it); a number on one line with the qualifier on the next still trips.
# Skip decision (documented, R3): bare '3/3' is NOT in the pattern set -
# live docs legitimately say 'make attest (3/3)' (docs/ops-notes.md:30)
# and the attest gate is 3/3 by design, so a bare pattern would
# false-positive. Only the corpus-context form '3/3 corpus' is guarded
# (0 legit hits live).
# Scope decision (documented, R4, Bheem rec): scan roots extended to
# README.md + development/ - the 68/1,360-class drift shipped twice
# inside those roots (tree §5 and README roadmap). Historical artifacts
# stay EXCLUDED (supersede-not-delete):
#   docs/superpowers/plans/   dated plan-time counts
#   development/builds/       dated phase report snapshots
# Scope decision (documented, R3 re-grade): docs/harness-contract.md's
# dated milestone-record paragraphs (P2.1/P3.5/P3.6/P3.7, the block
# before the first '## ' heading) are historical records
# (supersede-not-delete) - they legitimately say '36 SKILL.md' /
# '27 leaves' because they record what was true at that milestone.
# The guard scans only the LIVE sections below that heading; the
# current milestone record (P3.7) already carries the live numbers
# (52 SKILL.md / 43 leaves).
# This guard protects LIVE docs (marketing/ + docs/ + development/ +
# README.md), not the historical record.
# Usage: bash ops/automation/stale-number-guard.sh [root_dir]
#   (optional root_dir override for fixture testing; default = repo root)
set -u
root="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
patterns='28/28|12 skills|twelve skills|twenty-eight|five installable|five packs|12 verified|12 aerospace( engineering)? skills|3/3 corpus|68 installable|1,360|\b27 skills\b|\b27 aerospace\b|\b27 leaf skills\b|\b9 packs\b|\b9 domain packs\b|\b9 installable\b|\b36 SKILL\.md\b'
exempt='planning target, not a shipped count'
fail=0

scan_file() {
  local f="$1"
  local hits
  case "$f" in
    */docs/superpowers/plans/*|*/development/builds/*) return ;;
  esac
  if [[ "$f" == */docs/harness-contract.md ]]; then
    # Dated milestone-record paragraphs (P2.1/P3.5/P3.6/P3.7, the block
    # before the first '## ' heading) are history (supersede-not-delete);
    # scan only the live sections below them.
    hits=$(awk '/^## /{live=1; next} live' "$f" | grep -Eni "$patterns" | grep -Evi "$exempt")
  else
    hits=$(grep -Eni "$patterns" "$f" 2>/dev/null | grep -Evi "$exempt")
  fi
  if [ -n "$hits" ]; then
    echo "FAIL stale-number-guard: stale count(s) in $f:"
    printf '%s\n' "$hits"
    fail=1
  fi
}

for root_name in marketing docs development; do
  dir="$root/$root_name"
  [ -d "$dir" ] || continue
  while IFS= read -r -d '' f; do
    scan_file "$f"
  done < <(find "$dir" -type f -print0)
done
[ -f "$root/README.md" ] && scan_file "$root/README.md"

if [ "$fail" -eq 0 ]; then
  echo "PASS stale-number-guard: no '28/28|12 skills|twelve skills|twenty-eight|five installable|five packs|12 verified|12 aerospace( engineering)? skills|3/3 corpus|68 installable|1,360|27 skills|27 aerospace|27 leaf skills|9 packs|9 domain packs|9 installable|36 SKILL.md' in marketing/ + docs/ + development/ + README.md (dated plans/, builds/ and harness-contract milestone records excluded; qualified README planning-target lines exempt)"
fi
exit "$fail"
