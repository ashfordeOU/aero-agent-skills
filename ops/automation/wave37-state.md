# Wave-37 state notes

- 2026-09-04 WAVE-37 close. Baseline (wave-36 close): 496 leaves, 85
  packs, 12 families, 1008 router tasks, 30 standards; HEAD 3c887595
  wave-36 close, brief commit 5f4c081d == remote main (ls-remote
  verified at dispatch). Ratings ledger 496 rows. CEO gate PASSED
  9.65/10 at wave-36. Quiet-hours gate green at dispatch (~18:04 UTC,
  exit 0); API health reachable (deepseek models HTTP 401 = reachable,
  0.29 s). Prep commit 6b72031d (builder kit, close runbook, merge/sim
  helpers, 10 specs at ops/automation/state/wave37-specs/).

## Fresh family receipts (this wave, deterministic word-boundary greps,
five probe rounds at the wave-37 HEAD + sibling fence reads)

Wave-36 receipts were re-probed FRESH at 496 leaves; every verdict below
carries a deterministic grep or a sibling-body quote:

- SES 34 (CEO-named airworthiness-management vein; wave-36 landed
  ica-cmr-ali-classification there and the streak broke): TWO genuine
  gaps - airworthiness-directive-compliance (in-service-safety-
  assessment treats the AD only as a corrective-action ROUTE output,
  "airworthiness-directive-request"; nobody evaluates an operator
  fleet's compliance with an issued directive) and type-certificate-
  data-sheet (whole-tree grep "type certificate data sheet"/"TCDS" =
  0 owners; certification-basis selects regulations/path, it does not
  compile or validate the data-sheet record). MRB disposition logic
  DECLINED with quoted sibling evidence: nonconformance-control owns
  "route repair and use-as-is dispositions through the material review
  board" (AS9100 clause 10.2). MRBR report DECLINED (msg3-maintenance-
  analysis develops the scheduled program that the MRBR documents).
  STC / change-classification DECLINED (fragmented across
  configuration-management + certification-basis + means-of-compliance;
  "major change/minor change" appears in configuration-management).
  permit-to-fly / certificate-of-airworthiness / airworthiness-review
  DECLINED (procedural, below the deterministic bar).
- AERO 36 dense receipt HOLDS: whirl-flutter probed deep and DECLINED
  on model-fidelity risk - the standard screening model couples pylon
  pitch/yaw through gyroscopic and ASYMMETRIC propeller-aero terms that
  drive the backward-whirl mechanism; a clean stdlib closed-form under
  the symmetric-pylon decoupling misses the mechanism and a 4-state
  eigen sweep is beyond the leaf pattern. laminar-flow-control /
  natural-laminar-flow DECLINED (boundary-layer-theory +
  boundary-layer-transition own the transition seam; NLF methods are
  empirical). 0 slots.
- PROP 37: ONE genuine gap - subsonic-inlet-recovery (whole-tree grep
  "ram recovery"/"inlet recovery"/"pressure recovery" = 0 owners outside
  ramjet-inlet, which is the SUPERSONIC ramjet intake; the gas-turbine-
  cycle/turbofan-cycle decks take the inlet recovery as an input).
  Rocket pressurant/feed DECLINED (cold-gas-thruster owns plenum
  blowdown, space-systems propellant-tank-sizing owns spacecraft
  pressurant mass, rocket-turbopump owns NPSP - fragmented near-
  owners); engine-matching DECLINED (compressor-map + turbofan-off-
  design context); turboshaft DECLINED (free-turbine owns).
- FTO 41 / GNC 41: receipts reaffirmed fresh. FTO DENSE (telemetry
  chain complete: telemetry-data-acquisition + pcm-telemetry-
  decommutation; instrumentation, planning, safety, envelope,
  performance packs all in-leaf; high-speed-taxi/aerial-refuel probed,
  procedural). GNC DENSE (sensor-fusion owned by kalman-filter-design;
  trajectory optimization by dymos-trajectory; h-infinity probed and
  declined on solver weight - CARE/gamma iteration beyond the anti-hang
  budget for a stdlib leaf this wave).
- AV 42: ONE genuine gap - holding-pattern-entry (whole-tree grep
  "holding pattern" = 0 owners; flight-planning does great-circle legs/
  vertical profile only; the 70/110 entry-sector rule, outbound-leg
  timing and 1-in-60 wind correction are deterministic). AFDX bandwidth
  DECLINED (arinc664-afdx ALREADY sizes VL bandwidth, jitter, latency
  and BAG); MIL-STD-1760 / cockpit-video probed, not deterministic.
- FM 42 / STRUCT 43: saturated receipts CONFIRMED fresh with quoted
  fences. ground-resonance OWNED by rotorcraft-lead-lag-dynamics
  ("ground-resonance clearance verdict" in its claim); stiffened-panel
  DECLINED (plate-buckling owns effective-width of stiffened skin AND
  fuselage-skin-stringer owns stringer strip sizing - fragmented);
  V-n diagram OWNED TWICE (gust-maneuver-loads constructs the V-n
  diagram and load-factor-envelope builds the flight-test V-n).
- CC 44: ONE genuine gap - grubbs-outlier-test, the WEAKEST-ACCEPTED
  candidate (same tier as wave-36 runs-test, disclosed): descriptive-
  statistics owns 1.5-IQR fence SCREENING with "no hypothesis testing"
  in its claim; Grubbs is the distinct parametric single-outlier test
  with a fixed critical-value table; zero owners. process-capability /
  acceptance-sampling ownership re-checked: process capability OWNED
  (statistical-process-control + measurement-systems-analysis + key-
  characteristic-management carry Cp/Cpk/Ppk); acceptance-sampling is
  NOT owned (0 owners for "AQL"/"acceptance sampling") and was placed
  in MQ as the genuine QC gap.
- SPACE 44: ONE genuine gap - geostationary-station-keeping
  (mission-delta-v-budget takes station keeping as an INPUT line;
  three-body-libration owns libration-POINT sites only; walker-delta
  owns constellation design). TID/SEU DECLINED (radiation-debris owns
  dose, SEU and shielding).
- MQ 45: TWO genuine gaps - acceptance-sampling (above) and
  gage-rr-anova (WEAKEST-ACCEPTED alongside grubbs, disclosed):
  measurement-systems-analysis owns the RANGE-method Gage R&R and its
  body has ZERO mentions of ANOVA/variance components; the two-way
  ANOVA estimator with operator-by-part interaction is a distinct,
  standard method with zero owners.
- VD 47 (largest, probed ONLY because every smaller family above was
  provably exhausted or freshly satisfied): TWO genuine gaps in the
  deterministic subsystem-sizing class, fresh (not in the wave-36
  candidate/decline lists): electrical-wire-sizing (battery-sizing's
  voltage drop is the PACK branch drop; EWIS-installation-quality is
  install QUALITY not sizing; whole-tree "ampacity"/wire-run "voltage
  drop" = no owning sizing leaf) and hydraulic-actuator-sizing
  (hydraulic-system-sizing takes piston AREA as an input; control-
  surface-sizing ends at the hinge moment; landing-gear-retraction-
  sizing is that mechanism - nobody sizes bore/rod/buckling).
  engine-start declined (starter torque maps empirical), potable-water/
  de-ice/essential-battery declines re-confirmed (wave-36 convention).

## Wave plan

10 leaves (below the 12-16 band: exactly 10 genuine gaps survived the
deterministic bar across fresh probes of all 12 families; mandate is
land >=10 and never open a duplicate or pad; the two weakest candidates
are disclosed above and in the specs). Family spread at close:
systems-engineering-safety 34 -> 36, propulsion 37 -> 38, avionics 42 ->
43, cross-cutting 44 -> 45, space-systems 44 -> 45, manufacturing-quality
45 -> 47, vehicle-design 47 -> 49. Unchanged: aerodynamics 36,
flight-mechanics 42, flight-test-operations 41, gnc-autonomy 41,
structures 43. Total 506 leaves. 85 packs (no new pack). 12 routers.

## Spec math verification (ops, /tmp, BEFORE builders ran)

One verification script (ops/automation state helpers at /tmp) covered
every numeric anchor: AD remaining values (500 / -200 / -550 / -17.5 /
-502.5), TCDS validation lists, MIL-E-5008B ram recovery (1.0 at
M 0.82; 0.970578 at M 1.5) and face total pressure (154430 Pa),
GEO anchors (radius 42164.2 km, speed 3074.7 m/s, N/S 45.61 m/s/yr at
0.85 deg, E/W cycle 14.907 d at L 0.05 / A 0.0018, propellant 33.0 kg),
acceptance-sampling OC (0.9534 at p 0.01; 0.3748 at p 0.04), ANOVA GRR
fixture (percent_grr 13.19, ndc 10), wire ampacity/drop anchors
(18.0/25.1/32.8 A at 45 C; 1.128/0.710 V), Grubbs G 2.448 at the 12.5
sample, actuator anchors (bore 54.8 mm, rod 17.7 mm, mass 3.13 kg).
Two probe anchors corrected at prep: stagnation ratio at M 0.82 is
1.5552 (not 1.4785); OC at p 0.04 is 0.3748 (not 0.228). Builders took
their real module outputs as test targets within the spec bounds.

## Build batches + per-leaf commits (10 leaves, one agent per leaf)

- Batch 1 (4/4): systems-engineering-safety/continued-airworthiness/
  airworthiness-directive-compliance (2fa94568), .../type-certificate-
  data-sheet (6ea33ffe), propulsion/gas-turbine-cycle/subsonic-inlet-
  recovery (5b4d26aa), space-systems/orbit-mechanics/geostationary-
  station-keeping (749bc99c). Ledger rows 497-500.
- Batch 2 (4/4): manufacturing-quality/as9100/acceptance-sampling
  (518682bb), .../gage-rr-anova (72b248b2), vehicle-design/sizing/
  hydraulic-actuator-sizing (340c5e49, which ALSO swept the
  electrical-wire-sizing files - see disclosures), vehicle-design/
  sizing/electrical-wire-sizing (six artifacts + ledger row 501 ride
  inside 340c5e49; no separate commit). Ledger rows 501-504.
- Batch 3 (2/2): cross-cutting/numerics/grubbs-outlier-test
  (a4a296a0), avionics/flight-management/holding-pattern-entry
  (899a2b70). Ledger rows 505-506.
- 10/10 planned landed; mandate >=10 MET. Zero builder deaths. One
  ops steer to a builder (blocked python3 -c retries) which had already
  committed when the steer arrived. leaf-create-gate PASS on all 10
  leaves (ops re-ran the gate at each batch boundary: ad-compliance,
  acceptance-sampling, hydraulic-actuator-sizing, grubbs-outlier-test,
  holding-pattern-entry all PASS at the boundary check).
- Ledger rows 497-506 contiguous and unique at HEAD; header 496 -> 506
  at close. Corpus 1008 -> 1028 (20 tasks). Fragments deleted, 0 on
  disk.

## HIT@1 no-task-stealing check

- Pre-merge routing simulation (wave37-sim-merge.py on the corpus +
  on-disk fragments BEFORE the real merge): SIM PASS 1028/1028 Hit@1,
  ZERO pre-existing task thefts, no rewording needed (specs embedded
  1-2 of each leaf's own hyphenated tag tokens in the queries where a
  sibling holds a generic fragment - wave-36 lesson baked into the
  specs).
- Post-merge gate 5 at rest: make validate PASS 5/5 (1028/1028).

## GATES FRESH at rest (final HEAD 1aa98f6d)

- make validate PASS 5/5 (1028/1028 Hit@1 deterministic offline)
- make attest PASS 3/3 (number snapshot offline + brief audit +
  content-policy sweep 0 hits)
- make completeness ALL REQUIRED PASS
- make value-delta PASS (10/10 >= 0.2)
- visuals-check PASS (19 artifacts fresh, 506 leaves / 85 packs / 12
  families); manifest-check PASS (518 SKILL.md zero diff)
- router descs <= 1024 (all 12, wave16-router-desc-len.py PASS);
  router parity rows == leaves all 12 families
- REAL em dashes in skills/: 0 files / 0 lines (git grep at rest -
  receipt is true at HEAD 1aa98f6d; all 10 leaves written em-dash-free)
- stale-number-guard PASS (ops/automation/stale-number-guard.sh; the
  run-tests.sh wrapper referenced by the runbook does not exist in this
  checkout layout, the guard script IS the G7 test here and it PASSes)
- git status clean (tree clean)

## SPEC DEVIATIONS / disclosures

1. Wave plan 10 leaves (12-16 band not reached): exactly 10 genuine
   gaps survived the deterministic bar across the 12 families probed
   fresh; mandate (>=10 landed, no duplicates, no padding) is MET and
   the honest count is disclosed here. gage-rr-anova and grubbs-
   outlier-test are the weakest accepted candidates (both flagged in
   the receipts; same tier as wave-36 runs-test). Every other family
   receipt is quoted/declined above.
2. Shared-index race (wave-31..36 class) realized in batch 2: the
   hydraulic-actuator-sizing commit 340c5e49 swept the electrical-wire-
   sizing six artifacts + ledger row 501 into its commit. Verified at
   HEAD: electrical-wire-sizing SKILL.md, logic, contract test,
   fragment content (merged), eval record and ledger row are all on the
   HEAD chain - nothing lost, only commit granularity is coarser. No
   rewrite, per doctrine.
3. Naming-convention divergence: 3 batch-1 leaves (airworthiness-
   directive-compliance, type-certificate-data-sheet, subsonic-inlet-
   recovery) use HYPHENATED logic filenames (e.g.
   airworthiness-directive-compliance_logic.py) while the repo
   convention (ica-cmr-ali-classification etc.) is underscore. Both are
   leaf-create-gate-valid; the tests import the logic portably via
   importlib.util from the sibling dirname (no machine-local paths,
   no absolute sys.path). Left as-is to avoid churn; noted for the
   next kit (explicit underscore instruction).
4. AERO whirl-flutter declined on model-fidelity risk rather than on
   ownership (only such decline this wave) - documented in the
   receipts so the next probe does not re-litigate it.
5. The runbook line about ./ops/automation/test/run-tests.sh is stale
   for this checkout (no such path); the G7 stale-number guard runs
   directly via ops/automation/stale-number-guard.sh and PASSes.

## PUSH + PUBLISH RECEIPTS

- Private arjun-0077/aero-agent-skills: push ran as a background
  process (the pre-push hook runs the FULL battery: make validate
  5/5 with 1028/1028 Hit@1, make attest 3/3, visuals-check, manifest
  counts + entries, router parity, installer flattens/qualifies,
  MCP handshake + tools/list + search_skills + get_skill, CLI
  list/search/show, package smoke - all PASS, "pre-push: ALL GATES
  GREEN"). Push completed 5f4c081d..1aa98f6d main -> main,
  PUSH_EXIT=0; ls-remote verified remote main == local HEAD
  1aa98f6d. No Ashforde token on the private repo, no force, no
  visibility flip.
- publish-public.sh sanctioned sync: dev tree clean (make
  visuals-check), secrets + leak sweep clean, public-safety audit
  clean, full gate battery green INSIDE the export (3 min), mirror
  sync + leaf-count guard PASS (export 506 >= public 496, no
  regression), push to ashfordeOU/aero-agent-skills normal
  fast-forward no force, PASS at a514d587 (506 skills, 85 packs, 12
  families); About refreshed from the mirror post-push (2da34f0e +
  eec11e34 fixes intact).
- Public HEAD verified a514d587 via ls-remote; GitHub CI attest
  SUCCESS and release-on-milestone SUCCESS for a514d587 (polled via
  gh as arjun-0077; attest 4m22s, release-on-milestone 53s).
- GROUP 160 close-out post sent as Ops Manager, SEND_EXIT = 0.

## Lessons (for wave-38)

- The CEO-named SES vein paid twice (AD compliance + TCDS): when a
  wave breaks a saturation streak in a sub-area, probe that sub-area
  HARD next wave before re-declaring density - the ica-cmr landing was
  the tip of the vein, not the whole seam.
- "0 owners" is necessary but not sufficient: the probes that found
  AFDX bandwidth, V-n, stiffened-panel and rocket pressurant all had 0
  raw hits but sibling claims owned the function (arinc664-afdx sizes
  the network itself; gust-maneuver-loads AND load-factor-envelope both
  construct the V-n; plate-buckling + fuselage-skin-stringer split
  stiffened-skin work; cold-gas + propellant-tank-sizing + turbopump
  split the rocket pressurization seam). Read the sibling CLAIM before
  accepting a zero-owner grep.
- Spec corpus queries with the leaf's own hyphenated tag tokens baked
  in (wave-36 lesson) produced a clean pre-merge sim with ZERO
  rewording for the second wave running.
- Add an explicit "underscore script filenames" line to the builder
  kit template (3 of 10 builders defaulted to hyphenated logic
  filenames; gate-valid but inconsistent with the 500-leaf convention).
- Expect the pre-push hook battery to exceed a 180 s foreground
  terminal timeout: run the wave push as a background process with
  notify-on-complete.
- Next: CEO P5.2 WAVE-37 audit >= 9.5 -> WAVE-38.
