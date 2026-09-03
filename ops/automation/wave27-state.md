# Wave-27 state notes

- 2026-09-03 WAVE-27 close: 14/14 planned leaves landed (founder
  mandate >=10 MET +4), close-out at HEAD a440e453 (private
  arjun-0077/aero-agent-skills, pushed via GITHUB_TOKEN_ARJUN and
  ls-remote verified remote main == a440e453 == HEAD). Full brief:
  ops/automation/wave27-brief.md (c87f6a5f). Public sync completed via
  publish-public.sh at 890c786c (379 skills, 83 packs, 12 families),
  CI attest run 33774817699 SUCCESS (plus release-on-milestone SUCCESS
  run 33774817700).

- LEAVES (365 -> 379, rate-at-creation 9.5 in-turn, rows 366-379,
  appended by each builder at creation, no duplicates):
  flight-mechanics/stability-control/deep-stall-analysis (28fc4c51),
  flight-mechanics/performance/speed-stability (3d21f37c),
  flight-mechanics/handling-qualities/pitch-bandwidth-criteria
  (62e1c9ab), aerodynamics/wing-design/winglet-design (b5950a98 +
  ba55dbe7 prose refine), gnc-autonomy/guidance/dubins-path-planning
  (6f7c9655), gnc-autonomy/navigation/gnss-pseudorange-positioning
  (7a49f96d), propulsion/gas-turbine-cycle/afterburner-cycle
  (5accd7c5), propulsion/axial-compressor/turbine-blade-cooling
  (dd35fe1d), space-systems/orbit-mechanics/gravity-assist-swingby
  (b4683492), space-systems/orbit-mechanics/conjunction-assessment
  (36fff0af), structures/composites/adhesive-bonded-joints
  (244aa075), structures/loads/shock-response-spectrum (860be834),
  avionics/flight-management/radio-navigation-aids (9623808a),
  avionics/flight-management/rnp-anp-containment (8d81c443).
  Every leaf shipped the per-skill completeness standard (SKILL.md +
  stdlib logic + offline unittest + eval fragment + value-delta JSON +
  ledger row). All 14 contract tests re-run by ops at HEAD: PASS.
  All 28 new corpus tasks Hit@1 to their own leaf.

- FLIGHT-MECHANICS FIRST (smallest-first honored): flight-mechanics
  (29, smallest) received 3 leaves, its first since wave-24. Wave-26
  had recorded zero clean FM gaps (ceiling -> climb-performance,
  balanced-field/V1 -> accelerate-stop-distance, Vmc ->
  v-speeds/oei-climb-gradient). Wave-27 found three genuine
  non-overlapping gaps by pushing into tool/artifact and
  deeper-standards territory: deep-stall alpha-lock analysis
  (stability-control; spin-recovery owns spinning regimes, not the
  T-tail blanking post-stall trim), speed-stability classification on
  the back side of the thrust-required curve (performance; the
  thrust-required leaf computes the curve and min speeds but does not
  classify trim speed stability), and the MIL-STD-1797A bandwidth /
  phase-delay criterion (handling-qualities; the mil-std-1797a leaf
  grades modal tables, not the frequency-domain method). Rejected as
  duplicates during prep: dedicated dutch-roll-mode-analysis
  (lateral-directional-stability explicitly claims the simplified
  yaw-sideslip Dutch roll model), maneuver-point / stick-force-per-g
  (control-surface-effectiveness owns elevator-per-g and stick force),
  time-to-climb (climb-performance), ceiling / balanced-field / Vmc
  (wave-26 receipts still hold).

- FAMILY SPREAD after wave (365 -> 379): flight-mechanics 29 -> 32
  (+3), aerodynamics 30 -> 31 (+1), avionics 30 -> 32 (+2),
  gnc-autonomy 30 -> 32 (+2), propulsion 30 -> 32 (+2), space-systems
  30 -> 32 (+2), structures 30 -> 32 (+2); the 31-count families
  (cross-cutting, flight-test-operations, manufacturing-quality,
  vehicle-design) and systems-engineering-safety (32, largest) were
  untouched by design per smallest-first doctrine.

- CORPUS 744 -> 772 tasks (28 new, 14 fragments merged via
  state/wave27-merge-corpus.py then deleted, 0 on disk), grep
  verified. 7 family routers updated parent-side (one table row + one
  routing-guidance bullet each: flight-mechanics, aerodynamics,
  gnc-autonomy, propulsion, space-systems, structures, avionics),
  all router descriptions <= 1024 chars verified via
  wave16-router-desc-len.py PASS (flight-mechanics 983, gnc-autonomy
  1021, avionics 857 maxes unchanged). Router parity check PASS for
  all seven updated families (rows == leaves: 32/31/32/32/32/32/32).
  Ledger header updated 365 -> 379 (rows 1-379 contiguous, no
  duplicates, 14 new rows). Visuals regenerated via make visuals
  (design locked, numbers only; visuals-check PASS 19 artifacts fresh,
  379 leaves / 83 packs); manifest regenerated (391 SKILL.md).
  Deep-stall-analysis SKILL.md desc-lint fix: description lacked the
  explicit 'Use when you must' clause required by gate 2, caught at
  close, patched, re-ran validate PASS (the builder's own verify had
  missed the gate-2 clause style).

- HIT@1 NO-TASK-STEALING: gate 5 re-run after the merge returned
  772/772 PASS with ZERO pre-existing tasks stolen. Specs were written
  with distinctive hyphenated tokens per sibling fence tables; no
  reword of any pre-existing corpus task was needed this wave (no
  wave-24R / wave-26 p1 recurrence).

- GATES FRESH at rest HEAD a440e453: make validate 5/5 (772/772 Hit@1
  deterministic offline), make attest 3/3, make completeness ALL
  REQUIRED PASS, make value-delta PASS (10/10 >= 0.2), visuals-check
  PASS (19 artifacts fresh), manifest-check PASS, router descs <=
  1024, em dashes 0 in skills/, stale-number-guard PASS, tree clean.
  Pre-push hook re-ran the full gate battery and verified before each
  private push.

- Push PRIVATE via arjun token (GITHUB_TOKEN_ARJUN) fast-forward only
  5a5e0359 then a440e453, ls-remote verified remote main == a440e453
  == HEAD, no Ashforde token on the private repo, no visibility flip.
  publish-public.sh sanctioned sync: export ran the full gate battery
  inside, leaf-count guard (379 >= 365) passed, pushed 890c786c to
  ashfordeOU/aero-agent-skills (normal fast-forward, no force),
  verified 379 skills / 83 packs / 12 families. GitHub CI attest
  SUCCESS (run 33774817699), release-on-milestone SUCCESS (run
  33774817700).

- SPEC DEVIATIONS / disclosures:
  1. speed-stability spec carried a factor-2 error in the analytic
     dT/dV induced term; the builder's smoke test caught that the
     derivative zero did not coincide with the (correct) closed-form
     minimum-drag speed. Ops steered the correct coefficient 4
     (exact derivative of T = cd0*q*S + k*W^2/(q*S)), the builder
     documented the correction in the logic docstring and test header,
     and added a derivative-zero-on-v_md unittest plus a
     finite-difference check. Approved spec adaptation, recorded
     in-tree.
  2. adhesive-bonded-joints test file used a machine-local absolute
     sys.path; publish-public.sh's leak sweep caught it in the export
     and aborted safely (nothing pushed). Ops fixed it to the portable
     os.path.dirname(os.path.abspath(__file__)) pattern (a440e453)
     and re-ran the publish. Lesson: builders must use the sibling
     portable import pattern, and the publish leak sweep is a real
     safety net.
  3. Two builders went quiet mid-batch (pitch-bandwidth-criteria in
     batch 1, dubins-path-planning in batch 2) and were steered once
     each; both recovered without re-dispatch. All other builders ran
     clean on the anti-hang protocol. No builder died this wave
     (14/14).

- DISPATCH LESSON: 14 specs in four batches (4+4+4+2) from prep
  commit f5a0a96d in about 55 minutes of fan-out wall time. The
  per-spec math anchors (e.g. gravity-assist delta 119.43 deg,
  conjunction Pc 1.25e-3, SRS peak 16.5 g at 80 Hz, afterburner
  augmentation 1.405) matched builder smoke outputs, keeping
  verification mechanical. Live-transcript monitoring caught the two
  quiet builders mid-batch (steer, not re-dispatch). Sandbox note
  held: compound shell commands with nested $()/if blocks are blocked;
  run gates and checks as single simple commands or small written
  python scripts.

- Next: CEO P5.2 WAVE-27 audit >= 9.5 -> WAVE-28.
