#!/usr/bin/env bash
# Stale-number guard (R2 rework, Market rec #2).
# Scans live marketing/ and docs/ for stale corpus/skill/pack count claims
# that contradict the live repo state (66 tasks = 58 domain + 8 adversarial;
# 27 skills; 9 installable packs). Patterns:
#   '28/28'          P2.1-era Hit@1 count (live: 66/66)
#   '12 skills'      P2.1-era skill count (live: 27)
#   'twenty-eight'   P2.1-era corpus count (live: sixty-six)
#   'five installable'  P3.6-era pack count (live: nine)
# Dated historical plan artifacts (docs/superpowers/plans/) are EXCLUDED:
# supersede-not-delete - plan-time counts record what was true when the plan
# was written and are not rewritten as history.
# Usage: bash ops/automation/stale-number-guard.sh [root_dir]
#   (optional root_dir override for fixture testing; default = repo root)
set -u
root="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
patterns='28/28|12 skills|twenty-eight|five installable'
fail=0

for root_name in marketing docs; do
  dir="$root/$root_name"
  [ -d "$dir" ] || continue
  while IFS= read -r -d '' f; do
    case "$f" in
      */docs/superpowers/plans/*) continue ;;
    esac
    if grep -En "$patterns" "$f" >/dev/null 2>&1; then
      echo "FAIL stale-number-guard: stale count(s) in $f:"
      grep -En "$patterns" "$f" || true
      fail=1
    fi
  done < <(find "$dir" -type f -print0)
done

if [ "$fail" -eq 0 ]; then
  echo "PASS stale-number-guard: no '28/28|12 skills|twenty-eight|five installable' in marketing/ + docs/ (dated plans/ excluded)"
fi
exit "$fail"
