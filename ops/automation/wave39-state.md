# Wave-39 state notes

- 2026-09-05 WAVE-39 close. Baseline (wave-38 close): 521 leaves, 85
  packs, 12 families, 1058 router tasks, 30 standards; HEAD d7528424
  wave-38 close, brief commit a26ef041 == remote main (ls-remote
  verified at dispatch ~10:33 UTC). Ratings ledger 521 rows. CEO gate
  PASSED 9.68/10 at wave-38. Quiet-hours gate green at dispatch (exit
  0); API health reachable (deepseek HTTP 401 = reachable, 0.29 s).
  Prep commit 5aff2926 (builder kit, close runbook, merge/sim helpers,
  15 specs at ops/automation/state/wave39-specs/, all anchors
  independently verified at prep by /tmp/w39-anchors.py: 83/83 PASS).

## Fresh family receipts (5 parallel read-only probe agents + ops
fence re-reads at the wave-39 HEAD a26ef041)

- SES 37 (CEO-named candidates zonal-safety-analysis /
  common-cause-analysis / particular-risk-analysis were ALREADY LANDED
  at this HEAD - the brief list was stale; probes verified). Whole-family
  probe found TWO genuine gaps in arp4761a: failure-mode-criticality
  (rate-based MIL-STD-1629A style C_m = beta*alpha*lambda*t; the RPN
  S*O*D rating function is owned by manufacturing-quality/as9100/risk-
  management so this leaf deliberately implements the rate-based
  criticality only) and beta-factor-analysis (CCF beta-factor
  quantification; common-cause-analysis owns qualitative ZSA/PRA/CMA
  coverage only and reliability-block-diagram's own pitfall defers CCFs
  to a leaf that cannot compute a probability). fta-fmea FMEA content
  verified severity-to-DAL only; RPN trap verified and fenced.
- AERO 38: ONE genuine gap: bow-shock-standoff (Billig-form sphere and
  cylinder standoff correlations; hypersonic-flow is force-only,
  oblique-shock owns the detached criterion only). turbulent-boundary-
  layer-integral was probed and DROPPED at spec time: Head-entrainment
  closure constants are empirically fragile (the printed H1(H) pair is
  discontinuous at the branch point and source variants disagree) -
  same model-fidelity bar as the wave-38 stringer-crippling decline;
  disclosed here. e-n transition, reference-enthalpy, wedge-heating
  declined with receipts.
- PROP 40: TWO genuine gaps: turbojet-cycle (compressor-turbine work
  balance is the missing middle; afterburner-cycle's own docstring
  delegates the core upward; gas-turbine-cycle is shaft-power only) and
  rocket-gravity-loss (powered-ascent loss accounting; staging/sizing
  leaves cover the ideal equation only). axial-compressor-stage-design
  (0.45 confidence) NOT taken - velocity-triangle synthesis has an
  R/psi closure subtlety under the sibling's constant-ca convention.
  Pressurant/turboshaft/engine-matching declines stand.
- FTO 41 / GNC 41: saturated receipts reaffirmed with proof (0 slots).
- FM 42: saturated receipt OVERTURNED narrowly at the function level:
  breguet-range is jet/TSFC-only while breguet-endurance implements BOTH
  jet and prop branches - the propeller branch is missing on the range
  side. propeller-range landed (PSFC + prop efficiency range).
- STRUCT 45: ONE genuine gap: laminate-plate-buckling (orthotropic
  CLT-D-matrix energy-method counterpart of the isotropic-only
  plate-buckling leaf; laminate-stiffness is A-matrix-only).
  stringer-crippling not re-opened; continuous-turbulence PSD declined
  on numeric-integral fidelity.
- AV 46: zero gaps (function-verified saturated: FMS lateral path,
  FSW scheduling, surveillance, data-bus, DO-160/178C/254 all owned).
- SPACE 46: TWO genuine gaps: gravity-gradient-stabilization (gnc
  attitude-dynamics owns the torque/dynamics only; zero inertia-ratio
  criterion, libration or boom sizing anywhere) and synodic-launch-
  window (Earth-orbit daily windows and C3 energy owned, heliocentric
  recurrence unowned; zero synodic hits repo-wide).
- CC 48: SIX genuine gaps landed: chi-square-goodness-of-fit,
  kruskal-wallis-test, poisson-confidence-interval, power-analysis,
  exact-binomial-test (numerics) and fastener-position-tolerance-calc
  (tolerancing; Y14.5 fixed/floating formulas, position-tolerance-calc
  is verification-side only). ANOVA/Mann-Whitney/normality checks
  verified owned; not re-proposed.
- MQ 48: effectively saturated - one marginal candidate
  (nelson-control-chart-rules, MED-LOW: extends SPC's Western Electric
  4 with Nelson 5-8) NOT taken this wave; GRR ANOVA+range, Cp/Cpk, WE
  rules, I-MR, attribute charts, CUSUM/EWMA, both acceptance-sampling
  families all verified owned.
- VD 49: not probed (largest-last; smaller families yielded 15 genuine
  gaps).

## Wave plan

15 leaves (within the 12-16 band; all genuine non-overlapping gaps
that survived fresh probes + sibling claim reads + spec-time anchor
verification). Family spread at close: systems-engineering-safety 37 ->
39, aerodynamics 38 -> 39, propulsion 40 -> 42, flight-mechanics 42 ->
43, structures 45 -> 46, space-systems 46 -> 48, cross-cutting 48 ->
54. Unchanged: flight-test-operations 41, gnc-autonomy 41, avionics 46,
manufacturing-quality 48, vehicle-design 49. Total 536 leaves. 85 packs
(no new pack). 12 routers. Corpus 1058 -> 1088 (30 tasks). Ledger 521
-> 536 rows.

## Spec math verification (ops, /tmp, BEFORE builders ran)

/tmp/w39-anchors.py covered every numeric anchor in all 15 specs
(83 checks, 0 fails after fixes): FMECA criticalities (2e-3/2.5e-4/
3e-4, C_r 2.55e-3, share 0.78431, single-mode 1.2e-2), beta-factor CCF
(q_i^2 8.02748e-5, Q_cc 9.995e-4, Q_dual 1.079695e-3, independence
9.90058e-5, enhancement 10.9054), bow-shock standoff (sphere M8
0.15043, M4 0.17510, cylinder M8 0.41522, M4 0.51682), turbojet cycle
(Tt0 334.8, T03 764.7, f 0.0197, Tt5 1224.4, v9 1195.5, F/m 889.3,
TSFC 22.2 mg/Ns, eta_p 0.408), rocket-gravity-loss (160 s, 7.355 MN,
TWR 1.071, dv 2492.7, losses 1569.1/1109.5, effective 1383.2),
propeller range (PSFC 9.293e-8, R 1472.2 km), laminate buckling
(86.85 kN/m at m2n1, isotropic 16.20 MPa), gravity-gradient (n
1.1068e-3, period 6555 s = 109.2 min = 1.155 orbital periods, torque
36.8 uN m, boom 0.2 kg), chi2-GOF (2.0734 p 0.913; 61.81 p 1.93e-11;
3.6 p 0.0578), Kruskal-Wallis (H 7.2 p 0.0273), Poisson CI (12.401/
41.923/7.378 quantiles, bounds 0.02584/0.08734 and 0/0.0369), power
analysis (n 63 per group, prop n 44, achieved 0.8013), exact binomial
(P(X<=8) 0.1110, P(X<=2) 0.0355), fastener Y14.5 (0.40 total, split
0.20/0.20, min hole 6.75), synodic (779.9 d, 44.34 deg). Probe-reported
anchors CORRECTED at prep where wrong: chi2-GOF uniform stat 2.333 ->
2.0734, power-analysis proportion n 48 -> 44, exact-binomial cdf
0.1166 -> 0.1110, Poisson k=0 upper 0.0184 -> 0.0369 (probe arithmetic
errors), plus the achieved-power formula sign fix; the specs carry the
verified values.

## Build batches + per-leaf commits (15 leaves, one agent per leaf)

- Batch 1 (4/4): systems-engineering-safety/arp4761a/beta-factor-
  analysis (04a65728), systems-engineering-safety/arp4761a/failure-
  mode-criticality (51347762), aerodynamics/high-speed/bow-shock-
  standoff (ac917148), propulsion/gas-turbine-cycle/turbojet-cycle
  (ec8d8b52).
- Batch 2 (4/4): flight-mechanics/performance/propeller-range
  (29d20d4c), structures/composites/laminate-plate-buckling
  (2dbaee8c), space-systems/adcs/gravity-gradient-stabilization
  (66b261d9), propulsion/rocket/rocket-gravity-loss (cd346f4b).
- Batch 3 (4/4): cross-cutting/numerics/kruskal-wallis-test
  (b0484d9f), cross-cutting/numerics/poisson-confidence-interval
  (676de11e), cross-cutting/numerics/chi-square-goodness-of-fit
  (eb0a07e6), cross-cutting/numerics/power-analysis (63627427).
- Batch 4 (3/3): cross-cutting/tolerancing/fastener-position-
  tolerance-calc (bd3eab2e), space-systems/mission-design/synodic-
  launch-window (81848622), cross-cutting/numerics/exact-binomial-test
  (5d1254ee; one in-turn fix after a leaf-create-gate forbidden-token
  trip on its own boundary prose).
- 15/15 planned landed; mandate >=10 MET. One ops follow-up commit
  7e3f38cc (corpus query reword - see disclosures). Ledger rows 522-536
  contiguous and unique at HEAD (physical file order normalized to
  ascending at close); header 521 -> 536. Corpus 1058 -> 1088 (30
  tasks). Fragments deleted, 0 on disk.

## HIT@1 no-task-stealing check

- Pre-merge routing simulation (wave39-sim-merge.py on the corpus +
  on-disk fragments BEFORE the real merge): first run SIM FAIL on 2 NEW
  tasks (w39-poisson-confidence-interval-2 -> failure-rate-estimation,
  w39-turbojet-cycle-2 -> gas-turbine-cycle); both fragments reworded to
  embed the leaf's own hyphenated tag tokens (commit 7e3f38cc), rerun
  SIM PASS 1088/1088 Hit@1 with ZERO pre-existing task thefts and no
  rewording of pre-existing tasks.
- Post-merge gate 5 at rest: make validate PASS 5/5 (1088/1088).

## GATES FRESH at rest (final HEAD before state note)

- make validate PASS 5/5 (1088/1088 Hit@1 deterministic offline)
- make attest PASS 3/3 (number snapshot offline + brief audit +
  content-policy sweep 0 hits)
- make completeness ALL REQUIRED PASS
- make value-delta PASS (10/10 >= 0.2; sampler churn reverted to HEAD
  after the gate per wave-38 precedent)
- visuals-check PASS (19 artifacts fresh, 536 leaves / 85 packs);
  manifest-check PASS (548 SKILL.md zero diff)
- router descs <= 1024 (all 12, wave16-router-desc-len.py PASS);
  router parity rows == leaves on all 7 touched families (SES 39, AERO
  39, PROP 42, FM 43, STRUCT 46, SPACE 48, CC 54)
- REAL em dashes in skills/: 0 files / 0 lines (git grep at rest -
  receipt true at HEAD; all 15 leaves written em-dash-free)
- stale-number-guard PASS (ops/automation/stale-number-guard.sh)
- git status clean (tree clean)

## SPEC DEVIATIONS / disclosures

1. The CEO brief's four named SES candidates (zonal safety analysis,
   FMECA extension, common-cause analysis, particular-risk analysis)
   were assessed against the LIVE tree: three already exist at HEAD and
   were not re-proposed; the FMECA seam yielded the rate-based
   failure-mode-criticality leaf once the RPN variant was fenced to
   manufacturing-quality. Genuine gaps landed instead in beta-factor
   CCF quantification.
2. turbulent-boundary-layer-integral (AERO, probe-rated HIGH) was
   dropped at spec time on model fidelity: the Head-entrainment H1(H)
   closure constants could not be sourced to a consistent published pair
   (the primary printed source is discontinuous at the branch point;
   variants differ) - stringer-crippling precedent. Disclosed rather
   than baked-in. Spec slot reallocated within the 15-leaf plan.
3. One ops corpus reword commit 7e3f38cc after the pre-merge sim
   caught 2 new-task misroutes (see HIT@1 section). No pre-existing
   corpus tasks were touched.
4. value-delta-all sweep churn: one batch-1 builder ran make value-
   delta-all, rewriting 215 committed eval JSONs (sampler normalization
   differs from builder-created records: passed = passing test FILES not
   methods, baseline from term presence). All 215 files restored to HEAD
   (wave-38 precedent: the gate is a check; content side effects are
   reverted). Later batches were instructed to skip make value-delta.
5. Ledger rows 522-529 were appended out of physical order by
   concurrent builders (shared-file race); numbers were contiguous and
   unique throughout; the ops close normalized the physical row order to
   ascending before the header update.
6. failure-mode-criticality and bow-shock-standoff commits (51347762,
   ac917148) do not list eval/skill-ratings.md in their own stat: their
   ledger rows were swept into later commits via the shared index (wave
   16/31/38 class). Nothing lost; HEAD carries rows 523 and 524 exactly
   once.
7. exact-binomial-test is a mid-confidence leaf (test-vs-interval
   semantics; fence text states the NHST-vs-CI boundary explicitly).
8. All 15 leaves use UNDERSCORE script filenames per the wave-38 kit
   lesson (verified at HEAD).

## PUSH + PUBLISH RECEIPTS

- Private arjun-0077/aero-agent-skills: push ran as a background
  process (pre-push hook ran the FULL battery: make validate 5/5 with
  1088/1088 Hit@1, make attest 3/3, visuals-check, manifest counts +
  entries, router parity, installer flattens/qualifies, MCP handshake +
  tools/list + search_skills + get_skill, CLI list/search/show,
  package smoke - all PASS, "pre-push: ALL GATES GREEN"). Push completed
  a26ef041..7f6a48a1 main -> main, PUSH_EXIT=0; ls-remote verified
  remote main == local HEAD 7f6a48a1. No Ashforde token on the private
  repo, no force, no visibility flip.
- publish-public.sh sanctioned sync: PASS (gates green inside the
  export; leaf-count guard 536 >= 521 no regression; normal
  fast-forward to ashfordeOU/aero-agent-skills). Public HEAD verified
  via ls-remote == 699904861c3bd72d1e8eb4c87f3e485029a23339 (536
  skills, 85 packs, 12 families); GitHub CI attest SUCCESS (run
  33964498877) and release-on-milestone SUCCESS (run 33964498883) for
  699904861, polled via gh as arjun-0077. About refresh completed
  (non-fatal).
- GROUP 160 close-out post sent as Ops Manager, SEND_EXIT = 0.

## Lessons (for wave-40)

- Probe briefs must be executed against the LIVE tree: three of the
  CEO's four named SES candidates already existed at HEAD. The probes
  caught it; the wave plan followed the receipts, not the list.
- Empirical-closure candidates (Head entrainment, crippling charts)
  fail the same fidelity bar: verify the correlation constants are
  consistent AND continuous at spec time, not at build time. When the
  primary source's printed fit is discontinuous, drop the leaf and say
  so.
- Concurrent ledger appends scramble physical row order even when
  numbers stay contiguous; normalize at close.
- make value-delta-all is a full-tree record rewrite, not a sample;
  keep builders on the default gate and revert sampler churn at close
  (wave-38 precedent holds).
- Next: CEO P5.2 WAVE-39 audit >= 9.5 -> WAVE-40.
