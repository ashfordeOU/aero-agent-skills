#!/usr/bin/env bash
# AeroSkills attestation scripts — TDD test runner.
# Each test asserts a NEGATIVE case (script MUST exit 1 on violation),
# then the at-rest case (all scripts exit 0 on the real repo).
# Usage: bash ops/automation/test/run-tests.sh   (exit 0 = all assertions hold)
#
# Live-read caveat (P3.2): N1 and G1 call number-snapshot.sh --live, which
# reads the GitHub API via `gh` (authed arjun-0077). The suite is therefore
# offline-deterministic EXCEPT those two live reads — every other assertion
# runs with no network. Tolerance: N1 deliberately feeds a wrong expected
# value (fixture 100 vs live ~39k) so the live read MUST exit 1; G1 feeds the
# real register so the live read MUST exit 0 (stars within the register's
# tolerance_pct / tolerance_abs). If gh is missing, unauthenticated, or the
# API fails, the live reads exit non-zero (number-snapshot never silently
# falls back) and the suite fails — run `gh auth status` first.
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
# Concurrency guard (P3.1): parallel suite runs must never touch the COMMITTED
# state dir. Each run gets a PID-suffixed scratch state dir for its own
# evidence; the EXIT trap removes it. The old fixed-name backup/restore race
# (two overlapping runs both mv'ing state -> state.suite-bak, then deleting
# each other's restored state) is gone: committed ops/automation/state is
# never moved or deleted, so the tree is clean at rest by construction.
test_state="$state.suite-run.$$"
fixture_run=""
cleanup() { rm -rf "$test_state" "$fixture_run" 2>/dev/null; }
trap cleanup EXIT
export SNAPSHOT_STATE_DIR="$test_state"

# N1: live run against fixture with wrong expected value must exit 1
NUMBERS_YAML="$auto/test/fixture-tracked-wrong.yaml" \
  bash "$auto/number-snapshot.sh" --live >/dev/null 2>&1
check "N1 snapshot live detects drift (fixture 100 vs live ~39k)" 1 $?

# N2: offline with no snapshot present must exit 1 (never silent drift)
# Deletes the PID-scratch dir (SNAPSHOT_STATE_DIR), never the committed one.
rm -rf "$test_state" 2>/dev/null
NUMBERS_YAML="$auto/numbers.yaml" \
  bash "$auto/number-snapshot.sh" --offline >/dev/null 2>&1
check "N2 snapshot offline without snapshot exits 1" 1 $?

# ---- brief-audit.sh negative ----------------------------------------------
note "== brief-audit.sh =="
# N3: stale figure (38.0k vs canonical 39,925) must exit 1
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

# N7 (P2.1 rework): root regression - the sweep must resolve repo_root from
# ops/automation (../..) and scan nested roots INCLUDING skills/. The fixture
# tree plants a red flag in skills/dummy/SKILL.md; the pre-fix root (../../..)
# resolved above the repo and never scanned skills/ = vacuous green. Copy the
# CURRENT script into a PID-suffixed RUN copy of the fixture tree so the test
# tracks the real code AND parallel runs never mutate the committed fixture
# tree (each run plants and sweeps its own copy).
note "== content-policy-sweep.sh root regression =="
fixture_run="$auto/test/fixture-tree-run.$$"
cp -r "$auto/test/fixture-tree" "$fixture_run"
mkdir -p "$fixture_run/ops/automation"
cp "$auto/content-policy-sweep.sh" "$fixture_run/ops/automation/content-policy-sweep.sh"
bash "$fixture_run/ops/automation/content-policy-sweep.sh" >/dev/null 2>&1
check "N7 sweep with corrected root scans skills/ (plant found)" 1 $?
rm -rf "$fixture_run"

# ---- spec-lint compliance flags (gate 1 extension) ------------------------
# Each fixture is otherwise conformant and must trip EXACTLY the new check
# (license/compliance/standards/gated/metadata enforcement).
note "== spec-lint compliance flags =="
spec_lint="$repo_root/scripts/spec_lint.py"
for f in no-license bad-license bad-compliance standards-unknown \
         gated-mismatch gated-nonbool no-metadata empty-standards; do
  python3 "$spec_lint" "$auto/test/fixture-spec-$f.md" >/dev/null 2>&1
  check "S.$f spec-lint flags $f" 1 $?
done

# ---- pack inventory (domain-pack install tooling) -------------------------
# pack_inventory.py lists the domain packs an installer can install
# (founder directive 2026-08-31: per-domain pack installation). The
# inventory reads top-level domain/pack frontmatter on every SKILL.md;
# a SKILL.md missing those fields must exit 1 (an installer must never
# silently install an untyped skill).
note "== pack_inventory.py =="
pack_inv="$repo_root/scripts/pack_inventory.py"
pack_out=$(python3 "$pack_inv" 2>/dev/null)
check "P1 pack inventory on real repo exits 0" 0 $?
printf '%s\n' "$pack_out" | grep -q "packs=9 skills=27"
check "P2 pack inventory counts 9 packs 27 skills" 0 $?

pack_out=$(python3 "$pack_inv" --pack avionics 2>/dev/null)
check "P3 pack inventory --pack avionics exits 0" 0 $?
printf '%s\n' "$pack_out" | grep -q "packs=1 skills=9"
check "P4 pack inventory --pack avionics counts 9 leaves" 0 $?

pack_out=$(python3 "$pack_inv" --domain systems-engineering-safety 2>/dev/null)
check "P5 pack inventory --domain systems-engineering-safety exits 0" 0 $?
printf '%s\n' "$pack_out" | grep -q "packs=1 skills=5"
check "P6 pack inventory --domain systems-engineering-safety counts 5 leaves" 0 $?

python3 "$pack_inv" "$auto/test/fixture-pack-bad" >/dev/null 2>&1
check "P7 pack inventory flags missing domain/pack frontmatter" 1 $?

python3 "$pack_inv" "$auto/test/fixture-pack-router-bad" >/dev/null 2>&1
check "P8 pack inventory flags router pack != router folder" 1 $?

python3 "$pack_inv" "$auto/test/fixture-pack-domain-bad" >/dev/null 2>&1
check "P9 pack inventory flags domain not in taxonomy" 1 $?

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

# G6: real skills tree passes the extended gate 1 (spec lint, compliance flags)
bash "$repo_root/scripts/gate-spec-lint.sh" >/dev/null 2>&1
check "G6 spec-lint gate on real skills tree exits 0" 0 $?

# No restore needed: committed ops/automation/state was never touched; the
# PID-scratch state dir is removed by the EXIT trap.

note ""
if [ "$fail" -eq 0 ]; then
  note "ALL TESTS PASS"
else
  note "SOME TESTS FAILED"
fi
exit "$fail"
