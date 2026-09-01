#!/usr/bin/env bash
# Stale-number guard (R2 rework, Market rec #2; ops track extended R3;
# scan roots extended R4; Wave-5 stale class + release-notes exemption R5).
# Scans LIVE corpus/skill/pack count claims that contradict the live
# repo state (216 tasks / 100 leaf skills / 12 installable packs; 50x20
# tree: 73 packs, 1,460 leaf skills, Wave 4 100 -> 940). Patterns:
#   '28/28'             P2.1-era Hit@1 count (live: 126/126)
#   '12 skills'         P2.1-era skill count, digit form (live: 55)
#   'twelve skills'     P2.1-era skill count, word form (live: fifty-five)
#   'twenty-eight'      P2.1-era corpus count (live: one hundred twenty-six)
#   'five installable'  P3.6-era pack count (live: twelve)
#   'five packs'        P3.6-era pack count, literal form (live: twelve) [R3]
#   '12 verified'       P2.1-era skill count, 'verified' form (live: 112);
#                       word-boundary so '112 verified skills' is not a
#                       false positive [R7]
#   '12 aerospace ...'  P2.1-era skill count, marketing form (live: 55);
#                       narrowed R4 to '12 aerospace( engineering)? skills'
#                       so the tree's legit '12 aerospace disciplines'
#                       (12 families) is not a false positive
#   '3/3 corpus'        P2.1-era corpus-ratio claim, corpus context (live: 126/126) [R3]
#   '68 installable'    R1-era 50x20 pack count (live: 73) [R4]
#   '1,360'             R1-era 50x20 leaf-skill total (live: 1,460) [R4]
#   '27 skills'         P5.1-era leaf-skill count (live: 55) [R3 re-grade]
#   '27 aerospace'      P5.1-era leaf count, marketing form (live: 55)
#   '27 leaf skills'    P5.1-era leaf count, 'leaf' form (live: 55)
#   '9 packs'           P5.1-era family mislabel (live: 35 sub-domain
#                       packs / 12 family routers). Bare digit form only:
#                       'sub-domain packs' without the bare count is
#                       legit ('35 live sub-domain packs',
#                       '73 sub-domain packs'), and '12 pack routers'
#                       is the live router count - neither trips
#   '9 domain packs'    P5.1-era family mislabel, 'domain' form
#   '9 installable'     P5.1-era pack count, digit form (live docs say
#                       'twelve installable domain packs' in words)
#   '36 SKILL.md'       P5.1-era SKILL.md total (live: 67)
#   '43 skills'         Wave-5-era leaf count, bare/digit form (live: 55) [R5]
#   '43 leaf skills'    Wave-5-era leaf count, 'leaf' form (live: 55) [R5]
#   '43 verified'       Wave-5-era leaf count, 'verified' form (live: 55) [R5]
#   '52 SKILL.md'       Wave-5-era SKILL.md total (live: 67) [R5]
#   '102/102'           Wave-5-era Hit@1 count (live: 126/126) [R5]
#   '102 tasks'         Wave-5-era corpus count (live: 126) [R5]
#   '83 skills'         Wave-4-fanout-era leaf count, bare/digit form (live: 100) [R6]
#   '83 leaf skills'    Wave-4-fanout-era leaf count, 'leaf' form (live: 100) [R6]
#   '83 verified'       Wave-4-fanout-era leaf count, 'verified' form (live: 100) [R6]
#   '95 SKILL.md'       Wave-4-fanout-era SKILL.md total (live: 112) [R6]
#   '182/182'           Wave-4-fanout-era Hit@1 count (live: 216/216) [R6]
#   '182 tasks'         Wave-4-fanout-era corpus count (live: 216) [R6]
#   '100 skills'        Wave-5-fanout-era leaf count, bare/digit form (live: 112) [R7]
#   '100 leaf skills'   Wave-5-fanout-era leaf count, 'leaf' form (live: 112) [R7]
#   '100 verified'      Wave-5-fanout-era leaf count, 'verified' form (live: 112) [R7]
#   '112 SKILL.md'      Wave-5-fanout-era SKILL.md total (live: 124) [R7]
#   '216/216'           Wave-5-fanout-era Hit@1 count (live: 240/240) [R7]
#   '216 tasks'         Wave-5-fanout-era corpus count (live: 240) [R7]
#   '112 skills'        Wave-5-close-era leaf count, bare/digit form (live: 122) [R8]
#   '112 leaf skills'   Wave-5-close-era leaf count, 'leaf' form (live: 122) [R8]
#   '112 verified'      Wave-5-close-era leaf count, 'verified' form (live: 122) [R8]
#   '124 SKILL.md'      Wave-5-close-era SKILL.md total (live: 134) [R8]
#   '240/240'           Wave-5-close-era Hit@1 count (live: 258/258) [R8]
#   '240 tasks'         Wave-5-close-era corpus count (live: 258) [R8]
#   '122 skills'        Wave-6-close-era leaf count, bare/digit form (live: 131) [R9]
#   '122 leaf skills'   Wave-6-close-era leaf count, 'leaf' form (live: 131) [R9]
#   '122 verified'      Wave-6-close-era leaf count, 'verified' form (live: 131) [R9]
#   '134 SKILL.md'      Wave-6-close-era SKILL.md total (live: 143) [R9]
#   '258/258'           Wave-6-close-era Hit@1 count (live: 276/276) [R9]
#   '258 tasks'         Wave-6-close-era corpus count (live: 276) [R9]
#   '131 skills'        Wave-7-close-era leaf count, bare/digit form (live: 147) [R10]
#   '131 leaf skills'   Wave-7-close-era leaf count, 'leaf' form (live: 147) [R10]
#   '131 verified'      Wave-7-close-era leaf count, 'verified' form (live: 147) [R10]
#   '143 SKILL.md'      Wave-7-close-era SKILL.md total (live: 159) [R10]
#   '276/276'           Wave-7-close-era Hit@1 count (live: 308/308) [R10]
#   '276 tasks'         Wave-7-close-era corpus count (live: 308) [R10]
#   '147 skills'        Wave-8-close-era leaf count, bare/digit form (live: 162) [R11]
#   '147 leaf skills'   Wave-8-close-era leaf count, 'leaf' form (live: 162) [R11]
#   '147 verified'      Wave-8-close-era leaf count, 'verified' form (live: 162) [R11]
#   '159 SKILL.md'      Wave-8-close-era SKILL.md total (live: 174) [R11]
#   '308/308'           Wave-8-close-era Hit@1 count (live: 338/338) [R11]
#   '308 tasks'         Wave-8-close-era corpus count (live: 338) [R11]
#   '162 skills'        Wave-9-close-era leaf count, bare/digit form (live: 183) [R12]
#   '162 leaf skills'   Wave-9-close-era leaf count, 'leaf' form (live: 183) [R12]
#   '162 verified'      Wave-9-close-era leaf count, 'verified' form (live: 183) [R12]
#   '174 SKILL.md'      Wave-9-close-era SKILL.md total (live: 195) [R12]
#   '338/338'           Wave-9-close-era Hit@1 count (live: 380/380) [R12]
#   '338 tasks'         Wave-9-close-era corpus count (live: 380) [R12]
# All new forms are digit-form on purpose: the live one-way
# vocabulary ('twelve installable domain packs', '12 pack routers',
# '12 disciplines', '12 families', '131 leaf skills', '143 SKILL.md',
# '276/276', '47 live sub-domain packs', '73 sub-domain packs',
# '1,460', '131 -> 940') shares the numbers but never the stale
# digit-phrase shapes, so word-boundary patterns separate them.
# Exemption (documented, R4): lines carrying the explicit qualifier
# 'planning target, not a shipped count' are NOT stale shipped claims.
# README.md's roadmap copy (Content Writer track) names the old
# 68-pack/1,360-skill plan as a planning target (qualified), so the
# guard exempts exactly that qualifier; ANY unqualified '68 installable'
# or '1,360' claim still trips. The exemption is line-scoped: the
# qualifier must sit on the same line as the number (as README states
# it); a number on one line with the qualifier on the next still trips.
# Exemption (documented, R5): dated marketing release notes
# (marketing/release-notes-*.md) are historical release artifacts
# (supersede-not-delete) - they legitimately carry the count that was
# true at release time (43 skills / 52 SKILL.md / 102 tasks). Same
# class as dated plans/ and builds/; scan roots exclude them.
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
#   marketing/release-notes-*.md  dated release artifacts [R5]
# Scope decision (documented, R3 re-grade): docs/harness-contract.md's
# dated milestone-record paragraphs (P2.1/P3.5/P3.6/P3.7/P5.1, the block
# before the first '## ' heading) are historical records
# (supersede-not-delete) - they legitimately say '36 SKILL.md' /
# '27 leaves' because they record what was true at that milestone.
# The guard scans only the LIVE sections below that heading; the
# current milestone record (P5.1) already carries the live numbers
# (67 SKILL.md / 55 leaves).
# This guard protects LIVE docs (marketing/ + docs/ + development/ +
# README.md), not the historical record.
# Usage: bash ops/automation/stale-number-guard.sh [root_dir]
#   (optional root_dir override for fixture testing; default = repo root)
set -u
root="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
patterns='28/28|12 skills|twelve skills|twenty-eight|five installable|five packs|\b12 verified\b|12 aerospace( engineering)? skills|3/3 corpus|68 installable|1,360|\b27 skills\b|\b27 aerospace\b|\b27 leaf skills\b|\b9 packs\b|\b9 domain packs\b|\b9 installable\b|\b36 SKILL\.md\b|\b43 skills\b|\b43 leaf skills\b|\b43 verified\b|\b52 SKILL\.md\b|\b102/102\b|\b102 tasks\b|\b83 skills\b|\b83 leaf skills\b|\b83 verified\b|\b95 SKILL\.md\b|\b182/182\b|\b182 tasks\b|\b100 skills\b|\b100 leaf skills\b|\b100 verified\b|\b112 SKILL\.md\b|\b216/216\b|\b216 tasks\b|\b112 skills\b|\b112 leaf skills\b|\b112 verified\b|\b124 SKILL\.md\b|\b240/240\b|\b240 tasks\b|\b122 skills\b|\b122 leaf skills\b|\b122 verified\b|\b134 SKILL\.md\b|\b258/258\b|\b258 tasks\b|\b131 skills\b|\b131 leaf skills\b|\b131 verified\b|\b143 SKILL\.md\b|\b276/276\b|\b276 tasks\b|\b147 skills\b|\b147 leaf skills\b|\b147 verified\b|\b159 SKILL\.md\b|\b308/308\b|\b308 tasks\b|\b162 skills\b|\b162 leaf skills\b|\b162 verified\b|\b174 SKILL\.md\b|\b338/338\b|\b338 tasks\b'
exempt='planning target, not a shipped count'
fail=0

scan_file() {
  local f="$1"
  local hits
  case "$f" in
    */docs/superpowers/plans/*|*/development/builds/*|*/marketing/release-notes-*) return ;;
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
  echo "PASS stale-number-guard: no '28/28|12 skills|twelve skills|twenty-eight|five installable|five packs|12 verified|12 aerospace( engineering)? skills|3/3 corpus|68 installable|1,360|27 skills|27 aerospace|27 leaf skills|9 packs|9 domain packs|9 installable|36 SKILL.md|43 skills|43 leaf skills|43 verified|52 SKILL.md|102/102|102 tasks|83 skills|83 leaf skills|83 verified|95 SKILL.md|182/182|182 tasks|100 skills|100 leaf skills|100 verified|112 SKILL.md|216/216|216 tasks|112 skills|112 leaf skills|112 verified|124 SKILL.md|240/240|240 tasks|122 skills|122 leaf skills|122 verified|134 SKILL.md|258/258|258 tasks|131 skills|131 leaf skills|131 verified|143 SKILL.md|276/276|276 tasks|147 skills|147 leaf skills|147 verified|159 SKILL.md|308/308|308 tasks' in marketing/ + docs/ + development/ + README.md (dated plans/, builds/, release-notes and harness-contract milestone records excluded; qualified README planning-target lines exempt)"
fi
exit "$fail"
