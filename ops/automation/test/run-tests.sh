#!/usr/bin/env bash
# AeroSkills attestation scripts — TDD test runner.
# Each test asserts a NEGATIVE case (script MUST exit 1 on violation),
# then the at-rest case (all scripts exit 0 on the real repo).
# Usage: bash ops/automation/test/run-tests.sh   (exit 0 = all assertions hold)
set -u
repo_root="$(cd "$(dirname "$0")/../../.." && pwd)"
auto="$repo_root/ops/automation"
state="$auto/state"
fail=0

note() { printf '%s\n' "$*"; }
check() { # check <label> <expected_exit> <actual_exit>
  if [ "$2" -eq "$3" ]; then
    note "PASS $1 (exit $3)"
  else
    note "FAIL $1 (expected exit $2, got $3)"
    fail=1
  fi
}

# ---- number-snapshot.sh negatives -----------------------------------------
note "== number-snapshot.sh =="
# Preserve the committed state dir so the suite leaves the tree EXACTLY as it
# found it (clean at rest even after running the tests); restored at the end.
state_backup="$state.suite-bak"
[ -d "$state" ] && mv "$state" "$state_backup"

# N1: live run against fixture with wrong expected value must exit 1
NUMBERS_YAML="$auto/test/fixture-tracked-wrong.yaml" \
  bash "$auto/number-snapshot.sh" --live >/dev/null 2>&1
check "N1 snapshot live detects drift (fixture 100 vs live ~39k)" 1 $?

# N2: offline with no snapshot present must exit 1 (never silent drift)
rm -rf "$state" 2>/dev/null
NUMBERS_YAML="$auto/numbers.yaml" \
  SNAPSHOT_STATE_DIR="$state" \
  bash "$auto/number-snapshot.sh" --offline >/dev/null 2>&1
check "N2 snapshot offline without snapshot exits 1" 1 $?

# ---- brief-audit.sh negative ----------------------------------------------
note "== brief-audit.sh =="
# N3: stale figure (38.0k vs canonical 39,111) must exit 1
bash "$auto/brief-audit.sh" "$auto/test/fixture-brief-stale.md" >/dev/null 2>&1
check "N3 brief-audit flags stale K-Dense 38.0k" 1 $?

# N5: derived drift — real largest-repo claim at a stale value must STILL exit 1
# (proves the summary-line tuning did not weaken the honest check)
bash "$auto/brief-audit.sh" "$auto/test/fixture-derived-stale.md" >/dev/null 2>&1
check "N5 brief-audit still flags largest-repo drift (19 vs 22)" 1 $?

# ---- content-policy-sweep.sh negative -------------------------------------
note "== content-policy-sweep.sh =="
# N4: ITAR-compliant claim in publishable content must exit 1
bash "$auto/content-policy-sweep.sh" "$auto/test/fixture-policy-bad.md" >/dev/null 2>&1
check "N4 content-policy-sweep flags ITAR-compliant" 1 $?

# ---- at-rest green ---------------------------------------------------------
note "== at-rest (real repo) =="
# Live snapshot once so offline has evidence, then offline audit
bash "$auto/number-snapshot.sh" --live >/dev/null 2>&1
check "G1 snapshot live on real register exits 0" 0 $?

bash "$auto/number-snapshot.sh" --offline >/dev/null 2>&1
check "G2 snapshot offline with snapshot exits 0" 0 $?

bash "$auto/brief-audit.sh" >/dev/null 2>&1
check "G3 brief-audit full repo exits 0" 0 $?

bash "$auto/content-policy-sweep.sh" >/dev/null 2>&1
check "G4 content-policy-sweep full repo exits 0" 0 $?

# G5: summary lines ("total ≈ 228 / N repos") must NOT be read as largest-repo
bash "$auto/brief-audit.sh" "$auto/test/fixture-derived-summary.md" >/dev/null 2>&1
check "G5 brief-audit summary line is not a largest-repo false positive" 0 $?

# Restore the committed state dir (discard evidence snapshots this run wrote)
rm -rf "$state" 2>/dev/null
[ -d "$state_backup" ] && mv "$state_backup" "$state"

note ""
if [ "$fail" -eq 0 ]; then
  note "ALL TESTS PASS"
else
  note "SOME TESTS FAILED"
fi
exit "$fail"
