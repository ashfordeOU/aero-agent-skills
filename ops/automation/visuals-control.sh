#!/usr/bin/env bash
# Negative control for visuals-check's raster freshness.
#
# `--check` used to assert only that each PNG EXISTED. A PNG made from an SVG
# that has since changed twice passes that forever, and on a host whose PATH
# omits the Homebrew prefix the generator could not find rsvg-convert at all:
# it printed WARN, skipped every raster, and exited 0. Nothing anywhere went
# red.
#
# docs/visuals.lock.json now records the sha256 of the SVG each PNG was made
# from -- the source, because PNG bytes are librsvg-version dependent and
# cannot be compared across machines. This plants a defect in that lock, one
# at a time, and requires visuals-check to go red AND name it.
#
# Runs on a THROWAWAY COPY. A control that edits the real lock file and
# restores it afterwards is one interrupt away from leaving the repository in
# the state it planted.
set -uo pipefail

REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/aero-visuals-control-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# The WHOLE tree, not a subset. gen_visuals derives its figures from the
# corpus, so a copy missing skills/ makes the baseline red for a reason that
# has nothing to do with any mutation -- and a VOID control says nothing
# about the gate.
( cd "$REPO" && tar --exclude .git --exclude __pycache__ -cf - . ) \
  | tar -xf - -C "$WORK"
cd "$WORK" || exit 2

LOCK=docs/visuals.lock.json
CHECK=(python3 scripts/gen_visuals.py --check)

if [ ! -f "$LOCK" ]; then
  echo "VOID: no $LOCK in this tree -- run \`make visuals\` once to establish it"
  exit 9
fi
cp "$LOCK" "$WORK/.lock.pristine"

echo "=== baseline: the unmutated copy must be green ==="
if ! out=$("${CHECK[@]}" 2>&1); then
  echo "VOID: baseline is not green, so no red below would mean anything"
  echo "$out" | tail -12 | sed 's/^/    /' 
  exit 9
fi
echo "  $(echo "$out" | grep -i PASS | tail -1)"
echo

pass=0; fail=0
grade () {  # grade <name> <expected-substring>
  local log rc
  log=$("${CHECK[@]}" 2>&1); rc=$?
  if [ $rc -eq 0 ]; then
    echo "  NOT PROVED  $1 -- stayed GREEN with the defect planted"
    fail=$((fail+1))
  elif grep -qi -- "$2" <<<"$log"; then
    echo "  RED-CAPABLE $1"
    echo "                -> $(grep -i -m1 -- "$2" <<<"$log" | sed 's/^ *//' | cut -c1-90)"
    pass=$((pass+1))
  else
    echo "  RED-VAGUE   $1 -- red, but never said '$2'"
    grep -iE "stale|fail" <<<"$log" | head -3 | sed 's/^/      /'
    fail=$((fail+1))
  fi
  cp "$WORK/.lock.pristine" "$LOCK"
}

echo "=== mutants: each must turn visuals-check red and name it ==="

python3 - <<'PY'
import json
p = "docs/visuals.lock.json"
d = json.load(open(p))
d["rasters"][sorted(d["rasters"])[0]] = "0" * 64
json.dump(d, open(p, "w"), indent=2)
PY
grade "a PNG made from an older SVG" "older SVG"

python3 - <<'PY'
import json
p = "docs/visuals.lock.json"
d = json.load(open(p))
del d["rasters"][sorted(d["rasters"])[0]]
json.dump(d, open(p, "w"), indent=2)
PY
grade "a PNG with no recorded source" "no recorded source"

rm -f "$LOCK"
grade "the lock file deleted entirely" "no recorded source"

FIRST_PNG=$(python3 -c "import json;print(sorted(json.load(open('$WORK/.lock.pristine'))['rasters'])[0])")
rm -f "$FIRST_PNG"
grade "the PNG itself deleted" "missing"

echo
if [ $fail -ne 0 ]; then
  echo "FAIL visuals-control: ${pass} red-capable, ${fail} NOT PROVED"
  exit 1
fi
echo "PASS visuals-control: ${pass} of ${pass} mutant(s) RED-CAPABLE, each red naming the planted defect"
