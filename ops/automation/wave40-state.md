# Wave-40 state notes

- 2026-09-05 WAVE-40 close. Baseline (wave-39 close): 536 leaves, 85
  packs, 12 families, 1088 router tasks, 30 standards; HEAD fb09a644
  wave-39 close; brief commit 32ad4265 == remote main (ls-remote
  verified at dispatch ~12:15 UTC). Ratings ledger 536 rows. CEO gate
  PASSED 9.68/10 at wave-39. Quiet-hours gate green at dispatch (exit
  0); API health reachable (deepseek HTTP 401 = reachable, 0.30 s).
  Prep commit 31f695a3 (builder kit, close runbook, merge/sim helpers,
  15 specs at ops/automation/state/wave40-specs/, all anchor-verified
  by executing python anchor scripts; spec-lint 15/15 PASS).

## Fresh family receipts (5 parallel read-only probe agents at the
wave-40 HEAD 32ad4265, receipts over lists honored)

- SES 39: CEO-named candidates from the brief were assessed FRESH:
  zonal-safety-analysis OWNED (full leaf, verified), FMECA
  detection/CA extension DECLINED (rate-based criticality owned by
  failure-mode-criticality, RPN fenced to manufacturing-quality,
  remaining CA columns qualitative), operational-safety-assessment
  DECLINED (O&SHA owns operational hazard; residual needs THERP
  human-error data), maintenance-task-analysis DECLINED (wave-38
  receipt: same function family as MSG-3). GENUINE gaps: (1)
  fault-tree-uncertainty-analysis (lognormal error-factor propagation
  to a top-event band + exceedance; importance-measures owns only
  point ranking; 0 distributional math in family), (2) ssa-closure
  (post-implementation closure layer, explicitly left open by PSSA
  "not interchangeable" + FHA "does not run the PSSA/SSA" pitfalls),
  (3) fmes-coverage-analysis (FMEA-to-FHA coverage; 0 FMES hits
  family-wide). common-mode-analysis-execution NOT taken (0.55 conf,
  token-collision risk with common-cause-analysis).
- AERO 39: named candidates resolved: turbulent-flat-plate-heating =
  OWNED duplicate (flat-plate-skin-friction-heating is laminar OR
  turbulent, fence quoted), SWBLI DECLINED (free-interaction plateau
  scatter + empirical heat-flux augmentation), real-gas DECLINED
  (multi-regime piecewise curve fits / chart-only effective gamma).
  ONE genuine gap landed: rough-wall-skin-friction (sand-roughness
  regime classification, fully-rough Cf closed form, trip criterion).
  hypersonic-viscous-interaction and tangent-wedge declined at 0.45
  (fidelity scrutiny; thin vein after 3 waves).
- FTO 41: 0 slots (saturated receipt reaffirmed with function scan).
- GNC 41: ONE genuine gap: ins-gnss-integrated-filter (loosely
  coupled error-state filter; kalman-filter-design scalar-only,
  inertial-navigation qualitative only). Router row for
  inertial-navigation had routed "INS/GPS integration" - the close
  adds the new leaf row parent-side; corpus sim verified zero theft.
- PROP 42: scramjet-cycle probe GAP conf 0.55 was DROPPED AT SPEC
  TIME: the house ramjet-cycle specific-thrust convention
  (F/mdot = a0 M0 (sqrt(tau_lambda) - 1)) does not extend cleanly to
  the supersonic-combustion cycle with a Rayleigh combustor; naive
  mirroring produced non-physical Isp magnitudes (37500 s at M0 = 5).
  Direct energy-bookkeeping with full Rayleigh total-pressure
  relations needs verification beyond this wave's fidelity bar -
  turbulent-boundary-layer-integral precedent, disclosed. All wave-39
  declines stood (drag loss, PPT, resistojet, pressurant, ablative,
  turboshaft/engine-matching/axial-stage).
- FM 43: balanced-field-length GAP conf 0.70 landed (V1 quadratic
  balance ASD == AGD; takeoff-performance all-engine-only fence
  quoted) + rotorcraft-range-endurance GAP conf 0.45 landed (hover
  endurance exact weight-decay integral + average-weight cruise
  closure; breguet fixed-L/D fence quoted). Declines stood:
  landing-with-obstacle owned, service ceiling owned, payload-range/
  reserve owned cross-family, Category-A declined.
- STRUCT 46: diagonal-tension-field-webs (Kuhn/NACA-TN-2661-era
  complete-diagonal-tension idealization with the sin(2a) = 1 plane
  value; torsion-shear-flow elastic-only, plate-buckling stops at
  tau_cr), peel-stress-bonded-joints (Goland-Reissner; adhesive-
  bonded-joints self-declares "peel and adherend bending are out of
  scope"), multiaxial-yield-criteria (von Mises/Tresca isotropic
  metals; failure-criteria is composite-lamina-only). stringer-
  crippling NOT re-opened. column-curves and multi-fastener
  distribution left at possible-tier (0.5/0.45).
- AV 46: 0 slots (function-level saturated reaffirmed).
- SPACE 48: ground-station-pass-planning (multi-pass contact schedule
  + downlink-gap layer; satellite-coverage single-pass geometry fence
  quoted) + magnetometer-calibration (scalar-checking batch bias
  estimation; 0 calibrat* hits in adcs pack). eigenaxis/wheel-
  unloading/orbit-insertion confirmed owned.
- MFG 48: 0 slots (Cpk owned in SPC; Pp/Ppk = extension not leaf;
  MSA complete).
- VD 49 (probed now that VD is not largest): cargo-compartment-sizing
  (ULD layout + door geometry), window-aperture-sizing (clamped
  circular pane from pressure differential; Roark documented
  constants), emergency-exit-configuration (discrete type/count
  rule tables). accumulator/refuel thin-slice/anti-skid declined.
- cross-cutting 54: NOT probed for slots; all 15 wave slots were
  filled by genuine smaller-family gaps (CC stays largest, untouched
  this wave).

## Landed leaves (15, all with own commits on the HEAD chain)

SES +3: fault-tree-uncertainty-analysis, ssa-closure,
fmes-coverage-analysis. AERO +1: rough-wall-skin-friction. FM +2:
balanced-field-length, rotorcraft-range-endurance. GNC +1:
ins-gnss-integrated-filter. STRUCT +3: multiaxial-yield-criteria,
diagonal-tension-field-webs, peel-stress-bonded-joints. SPACE +2:
magnetometer-calibration, ground-station-pass-planning. VD +3:
cargo-compartment-sizing, window-aperture-sizing,
emergency-exit-configuration. New totals: 551 leaves, 85 packs, 12
families, 1118 router tasks, 30 standards. Ledger 551 rows.

## HIT@1 / no-task-stealing

- Pre-merge routing simulation (state/wave40-sim-merge.py on the live
  corpus + 15 on-disk fragments): SIM PASS 1118/1118 Hit@1, zero
  pre-existing task theft, zero new-task misroutes. No corpus reword
  commit needed this wave.
- Corpus merged 1088 -> 1118 (state/wave40-merge-corpus.py), 15
  fragments deleted (0 on disk at close).

## Routers + ledger

- Family routers updated parent-side (7 families touched): one table
  row + one routing bullet per new leaf; rows == leaves per family
  (SES 42, AERO 40, FM 45, GNC 42, STRUCT 49, SPACE 50, VD 52);
  wave16-router-desc-len.py PASS (all <= 1024). Router frontmatter
  descriptions intentionally NOT edited (at the char cap; rows +
  bullets carry the parent-side update per wave-39 precedent).
- Ratings header 536 -> 551; rows 537-551 contiguous and physically
  ascending at close (one race recovery commit 0d9837ca added row 548
  for ground-station-pass-planning whose append was lost when a
  concurrent builder's commit overwrote the shared ledger - wave-39
  lesson #3 class; magnetometer's row 547 had been swept into the
  ground-station commit).

## Close-out gates FRESH at rest (run, not claimed)

- make validate 5/5 (1118/1118 Hit@1 deterministic offline)
- make attest 3/3 (number snapshot + brief audit + content policy)
- make completeness ALL REQUIRED PASS (563 skills)
- make value-delta 10/10 >= 0.2
- make visuals + visuals-check PASS (19 artifacts fresh: 551 leaves,
  85 packs); manifest-check PASS after the gate-2 desc fix
  regeneration (a775d82f)
- router descriptions <= 1024 (wave16-router-desc-len.py PASS)
- REAL em dashes in skills/: 0 files / 0 lines (git grep at rest -
  receipt true at HEAD; all 15 leaves written em-dash-free)
- ops/automation/stale-number-guard.sh PASS
- git status clean (tree clean at close commit 8c3d9a06; one manifest
  regeneration commit a775d82f after the desc-lint fix)

## SPEC DEVIATIONS / disclosures

1. scramjet-cycle (PROP, probe GAP conf 0.55) was dropped at spec
   time on cycle-convention fidelity: mirroring the house
   ramjet-cycle specific-thrust convention onto a Rayleigh
   supersonic-combustion cycle produced non-physical Isp magnitudes
   (about 37500 s at M0 = 5), and the direct energy-bookkeeping with
   full Rayleigh total-pressure relations was judged beyond the
   wave's verify-by-anchor bar. turbulent-boundary-layer-integral /
   stringer-crippling precedent. Slot reallocated to rotorcraft-range-
   endurance and the VD trio.
2. diagonal-tension-field-webs spec uses the Kuhn / NACA-TN-2661-era
   complete-diagonal-tension idealization with the plane-web
   sin(2 alpha) = 1 approximation (alpha = 45 degrees default, angle
   accepted as an input); the general variable-angle Kuhn solution was
   NOT implemented (chart-heavy). Disclosed in the spec body.
3. FTO 41 / AV 46 / MFG 48: 0 slots (saturated receipts reaffirmed
   with function coverage). cross-cutting 54 untouched (still the
   largest family; all 15 slots went to genuine smaller-family gaps).
4. Two GNC/PROP/FM spec-engineer dispatch attempts stalled on
   long-prompt model hangs (476+ s waiting for a model response each);
   both were stopped and the four specs (balanced-field-length,
   rotorcraft-range-endurance, ins-gnss-integrated-filter) were
   written by the ops manager inline with anchor scripts. scramjet-
   cycle dropped as above.
5. One pre-push hook battery failure (manifest stale because the
   gate-2 desc-lint fix landed after the visuals run) fixed with
   `make visuals` + regeneration commit a775d82f before the second
   push.
6. Ledger row 548 race recovery (see Routers + ledger above): the
   ground-station-pass-planning builder's ledger append was lost to a
   read-modify-write race with the magnetometer commit; ops added the
   row in 0d9837ca before the header update. wave-39 lesson #3 class.
7. All 15 leaves use UNDERSCORE script filenames and were written
   em-dash-free (verified at HEAD). All six artifacts per leaf on the
   HEAD chain.

## Lessons (for wave-41)

- Long-context spec-engineer prompts on this model stall with
  in-flight model-response hangs; a compact spec prompt with a hard
  write-NOW ordering beats an exhaustive one. When an anchor script is
  left behind by a stopped engineer, reuse it (peel, diagonal-tension,
  ground-station anchors recovered this wave and spec'd directly from
  real outputs).
- The pre-push hook battery re-runs manifest freshness from scratch:
  any leaf edit after the last `make visuals` (even a gate-fix word
  change) must be followed by `make visuals` before the push, or the
  hook fails on manifest staleness.
- Read-modify-write ledger races persist even at 3-4 concurrent
  builders; verifying every leaf's row on HEAD after each batch (and
  re-adding lost rows immediately) keeps the ledger honest.

## PUSH + PUBLISH RECEIPTS

- Private arjun-0077/aero-agent-skills: first push attempt was BLOCKED
  by the local pre-push battery on manifest staleness (the gate-2
  desc-lint fix for rotorcraft-range-endurance landed after the last
  `make visuals`); fixed with `make visuals` + regeneration commit
  a775d82f. Second push ran as a background process (pre-push hook ran
  the FULL battery: validate 5/5 with 1118/1118 Hit@1, attest,
  visuals-check, manifest counts + entries, router parity, installer
  flattens/qualifies, MCP handshake + tools/list + search_skills +
  get_skill, CLI list/search/show, package smoke - all PASS,
  "pre-push: ALL GATES GREEN"). Push completed 32ad4265..a775d82f
  main -> main, PUSH_EXIT=0; ls-remote verified remote main == local
  HEAD a775d82f. No Ashforde token on the private repo, no force, no
  visibility flip.
- publish-public.sh sanctioned sync: PASS (gates green inside the
  export; leaf-count guard 551 >= 536 no regression; normal
  fast-forward to ashfordeOU/aero-agent-skills). Public HEAD verified
  via ls-remote == 92eef9ca1dea3516f9fd84230caf7781aecb671b (551
  skills, 85 packs, 12 families); GitHub CI attest SUCCESS (run
  33970576096) and release-on-milestone SUCCESS (run 33970576076) for
  92eef9ca, polled via gh as arjun-0077. About refresh completed
  (non-fatal).
- GROUP 160 close-out post sent as Ops Manager, SEND_EXIT = 0.


