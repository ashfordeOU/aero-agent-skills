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
printf '%s\n' "$pack_out" | grep -q "packs=12 skills=183"
check "P2 pack inventory reports 'packs=12 skills=183' (12 family routers / 183 leaf skills)" 0 $?

pack_out=$(python3 "$pack_inv" --pack avionics 2>/dev/null)
check "P3 pack inventory --pack avionics exits 0" 0 $?
printf '%s\n' "$pack_out" | grep -q "packs=1 skills=16"
check "P4 pack inventory --pack avionics counts 16 leaves" 0 $?

pack_out=$(python3 "$pack_inv" --domain systems-engineering-safety 2>/dev/null)
check "P5 pack inventory --domain systems-engineering-safety exits 0" 0 $?
printf '%s\n' "$pack_out" | grep -q "packs=1 skills=13"
check "P6 pack inventory --domain systems-engineering-safety counts 13 leaves" 0 $?

python3 "$pack_inv" "$auto/test/fixture-pack-bad" >/dev/null 2>&1
check "P7 pack inventory flags missing domain/pack frontmatter" 1 $?

python3 "$pack_inv" "$auto/test/fixture-pack-router-bad" >/dev/null 2>&1
check "P8 pack inventory flags router pack != router folder" 1 $?

python3 "$pack_inv" "$auto/test/fixture-pack-domain-bad" >/dev/null 2>&1
check "P9 pack inventory flags domain not in taxonomy" 1 $?

# ---- stale-number guard (R2 rework, Market rec #2) -------------------------
# Greps live marketing/ + docs/ for stale corpus/skill/pack counts
# ('28/28', '12 skills', 'twenty-eight', 'five installable'); dated plan
# artifacts (docs/superpowers/plans/) are exempt (supersede-not-delete).
# R4 (Bheem rec): scan roots extended to README.md + development/ (the
# 68/1,360-class drift shipped twice inside those roots); dated
# development/builds/ reports stay exempt like plans/.
note "== stale-number-guard.sh =="
guard="$auto/stale-number-guard.sh"
bash "$guard" "$auto/test/fixture-stale-numbers" >/dev/null 2>&1
check "N8 stale-number guard flags stale counts in live marketing/ + docs/" 1 $?
bash "$guard" "$auto/test/fixture-stale-plans-only" >/dev/null 2>&1
check "N9 stale-number guard exempts dated plans/ (supersede-not-delete)" 0 $?
bash "$guard" "$auto/test/fixture-stale-roots" >/dev/null 2>&1
check "N12 stale-number guard flags planted 68/1,360 in README.md + development/" 1 $?
bash "$guard" "$auto/test/fixture-stale-roots-qualified" >/dev/null 2>&1
check "N13 stale-number guard exempts qualified README planning-target line" 0 $?
bash "$guard" "$auto/test/fixture-stale-builds-only" >/dev/null 2>&1
check "N14 stale-number guard exempts dated development/builds/ reports" 0 $?
# R3 re-grade (Ops track): 27/9/36-class stale counts ('27 skills',
# '27 aerospace', '27 leaf skills', '9 packs', '9 domain packs',
# '9 installable', '36 SKILL.md') that leaked past the R2/R4 patterns.
# Live one-way vocabulary ('35 live sub-domain packs', '12 family
# routers', '12 disciplines', '12 families', '73 sub-domain packs',
# '55 leaf skills', '67 SKILL.md') must NOT trip the new patterns.
bash "$guard" "$auto/test/fixture-stale-27-9-36" >/dev/null 2>&1
check "N15 stale-number guard flags planted 27/9/36-class counts ('27 skills' ... '36 SKILL.md')" 1 $?
bash "$guard" "$auto/test/fixture-legit-27-9" >/dev/null 2>&1
check "N16 stale-number guard exempts legit live vocabulary ('35 live sub-domain packs', '12 families', '55 leaf skills', '67 SKILL.md')" 0 $?
bash "$guard" "$auto/test/fixture-stale-9packs" >/dev/null 2>&1
check "N17 stale-number guard flags bare '9 packs' family mislabel" 1 $?
# R5 re-grade (Ops track): Wave-5 stale class ('43 skills', '43 leaf
# skills', '43 verified', '52 SKILL.md', '102/102', '102 tasks') that
# became stale when the wave pushed live counts to 55/67/126. Live
# vocabulary must NOT trip; dated release-notes carry the old counts
# by design and are exempt.
bash "$guard" "$auto/test/fixture-stale-43-class" >/dev/null 2>&1
check "N18 stale-number guard flags planted Wave-5-era counts ('43 skills' ... '102 tasks')" 1 $?
# R6 re-grade (Ops track): Wave-4-fanout stale class ('83 skills',
# '83 leaf skills', '83 verified', '95 SKILL.md', '182/182',
# '182 tasks') that became stale when the wave pushed live counts to
# 100/112/216. Live vocabulary must NOT trip.
bash "$guard" "$auto/test/fixture-stale-83-class" >/dev/null 2>&1
check "N19 stale-number guard flags planted Wave-4-era counts ('83 skills' ... '182 tasks')" 1 $?
bash "$guard" "$auto/test/fixture-legit-183-class" >/dev/null 2>&1
check "N20 stale-number guard exempts live wave-10 vocabulary ('183 leaf skills' ... '380 tasks')" 0 $?
# R7 re-grade (Ops track): Wave-5-fanout stale class ('100 skills',
# '100 leaf skills', '100 verified', '112 SKILL.md', '216/216',
# '216 tasks') that became stale when the wave pushed live counts to
# 112/124/240. Live vocabulary must NOT trip.
bash "$guard" "$auto/test/fixture-stale-100-class" >/dev/null 2>&1
check "N21 stale-number guard flags planted Wave-5-era counts ('100 skills' ... '216 tasks')" 1 $?
bash "$guard" "$auto/test/fixture-legit-183-class" >/dev/null 2>&1
check "N22 stale-number guard exempts live wave-10 vocabulary ('183 leaf skills' ... '380 tasks')" 0 $?
# R8 re-grade (Ops track): Wave-5-close stale class ('112 skills',
# '112 leaf skills', '112 verified', '124 SKILL.md', '240/240',
# '240 tasks') that became stale when Wave 6 pushed live counts to
# 122/134/258. Live vocabulary must NOT trip.
bash "$guard" "$auto/test/fixture-stale-112-class" >/dev/null 2>&1
check "N23 stale-number guard flags planted Wave-5-close-era counts ('112 skills' ... '240 tasks')" 1 $?
bash "$guard" "$auto/test/fixture-legit-183-class" >/dev/null 2>&1
check "N24 stale-number guard exempts live wave-10 vocabulary ('183 leaf skills' ... '380 tasks')" 0 $?
# R9 re-grade (Ops track): Wave-6-close stale class ('122 skills',
# '122 leaf skills', '122 verified', '134 SKILL.md', '258/258',
# '258 tasks') that became stale when Wave 7 pushed live counts to
# 131/143/276. Live vocabulary must NOT trip.
bash "$guard" "$auto/test/fixture-stale-122-class" >/dev/null 2>&1
check "N25 stale-number guard flags planted Wave-6-close-era counts ('122 skills' ... '258 tasks')" 1 $?
bash "$guard" "$auto/test/fixture-legit-183-class" >/dev/null 2>&1
check "N26 stale-number guard exempts live wave-10 vocabulary ('183 leaf skills' ... '380 tasks')" 0 $?
# R10 re-grade (Ops track): Wave-7-close stale class ('131 skills',
# '131 leaf skills', '131 verified', '143 SKILL.md', '276/276',
# '276 tasks') that became stale when Wave 8 pushed live counts to
# 147/159/308. Live vocabulary must NOT trip.
bash "$guard" "$auto/test/fixture-stale-131-class" >/dev/null 2>&1
check "N27 stale-number guard flags planted Wave-7-close-era counts ('131 skills' ... '276 tasks')" 1 $?
bash "$guard" "$auto/test/fixture-legit-183-class" >/dev/null 2>&1
check "N28 stale-number guard exempts live wave-10 vocabulary ('183 leaf skills' ... '380 tasks')" 0 $?
# R11 re-grade (Ops track): Wave-8-close stale class ('147 skills',
# '147 leaf skills', '147 verified', '159 SKILL.md', '308/308',
# '308 tasks') that became stale when Wave 9 pushed live counts to
# 162/174/338. Live vocabulary must NOT trip.
bash "$guard" "$auto/test/fixture-stale-147-class" >/dev/null 2>&1
check "N29 stale-number guard flags planted Wave-8-close-era counts ('147 skills' ... '308 tasks')" 1 $?
bash "$guard" "$auto/test/fixture-legit-183-class" >/dev/null 2>&1
check "N30 stale-number guard exempts live wave-10 vocabulary ('183 leaf skills' ... '380 tasks')" 0 $?
# R12 re-grade (Ops track): Wave-9-close stale class ('162 skills',
# '162 leaf skills', '162 verified', '174 SKILL.md', '338/338',
# '338 tasks') that became stale when Wave 10 pushed live counts to
# 183/195/380. Live vocabulary must NOT trip.
bash "$guard" "$auto/test/fixture-stale-162-class" >/dev/null 2>&1
check "N31 stale-number guard flags planted Wave-9-close-era counts ('162 skills' ... '338 tasks')" 1 $?
bash "$guard" "$auto/test/fixture-legit-183-class" >/dev/null 2>&1
check "N32 stale-number guard exempts live wave-10 vocabulary ('183 leaf skills' ... '380 tasks')" 0 $?

# ---- gated-set enumeration-completeness guard (R3 rework, Content rec #2) --
# Asserts numeric gated-set/map-coverage COUNT claims in the three
# enumeration docs (FAQ.md, glossary.md, positioning-1pager.md) match the
# live standards-map.yaml (10 gated:true of 16 total), and that explicit
# "all N gated standards" completeness claims name every gated standard.
note "== gated-set-check.sh =="
gated_set="$auto/gated-set-check.sh"
bash "$gated_set" "$auto/test/fixture-gated-stale" >/dev/null 2>&1
check "N10 gated-set check flags stale enumerations in live docs" 1 $?
bash "$gated_set" "$auto/test/fixture-gated-clean" >/dev/null 2>&1
check "N11 gated-set check passes clean enumerations" 0 $?

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

# G7: stale-number guard on the real repo must stay clean (R2 rework)
bash "$auto/stale-number-guard.sh" >/dev/null 2>&1
check "G7 stale-number guard on real repo exits 0" 0 $?

# G8: gated-set enumeration-completeness check on the real repo must stay
# clean (R3 rework). The live docs carry no numeric count claims that
# contradict standards-map.yaml (16 map entries, 10 gated:true).
bash "$auto/gated-set-check.sh" >/dev/null 2>&1
check "G8 gated-set check on real repo exits 0" 0 $?

# No restore needed: committed ops/automation/state was never touched; the
# PID-scratch state dir is removed by the EXIT trap.

note ""
if [ "$fail" -eq 0 ]; then
  note "ALL TESTS PASS"
else
  note "SOME TESTS FAILED"
fi
exit "$fail"
