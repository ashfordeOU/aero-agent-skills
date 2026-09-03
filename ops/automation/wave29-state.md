# Wave-29 state notes

- 2026-09-03 WAVE-29 close: 11/11 planned leaves landed (founder
  mandate >=10 MET +1), close-out at HEAD 8f1fa670 (private
  arjun-0077/aero-agent-skills, pushed via the arjun origin token and
  ls-remote verified remote main == 8f1fa670 == HEAD). Full brief:
  ops/automation/wave29-brief.md (512b16a8). Prep commit 8d25c0ec
  (builder kit + 11 specs + merge helper + 3 standards-map additions).
  Public sync completed via publish-public.sh at 037e53c8 (404 skills,
  85 packs, 12 families), leaf-count guard (404 >= 393) held, About
  refreshed from the mirror post-push; GitHub CI attest run 33789668500
  and release-on-milestone run 33789668506 both SUCCESS at close.

- LEAVES (393 -> 404, rate-at-creation 9.5 in-turn, rows 394-404
  appended by each builder at creation, no duplicates, header updated
  393 -> 404 at close):
  gnc-autonomy/navigation/gnss-raim-fde (8e07fd79),
  gnc-autonomy/estimation-filtering/rts-smoother (b3d41438),
  gnc-autonomy/guidance/coverage-path-planning (4714b8df),
  propulsion/rocket/cold-gas-thruster (a0724287),
  propulsion/turbomachinery/rocket-turbopump (1c3144e2),
  systems-engineering-safety/continued-airworthiness/
  msg3-maintenance-analysis (838e1b22),
  vehicle-design/sizing/canard-sizing (c15cc999),
  cross-cutting/numerics/cross-correlation-analysis (eaee7407),
  space-systems/subsystems/spacecraft-battery-sizing (80813a10),
  space-systems/orbit-mechanics/plane-change-maneuver (8402e80d),
  avionics/surveillance/tcas-resolution-advisory (3c9b320c, NEW
  surveillance pack - first leaf).
  Every leaf shipped the per-skill completeness standard (SKILL.md +
  stdlib logic + offline unittest + eval fragment + value-delta JSON +
  ledger row). All 11 contract tests re-run by ops at HEAD: PASS
  (unittest counts 30-45 per leaf, 394 total methods). All 22 new
  corpus tasks Hit@1 to their own leaf.

- SMALLEST-FIRST honored: the six 32-count families were re-probed
  first (wave-old receipts per the brief). Genuine gaps found and
  filled: gnc-autonomy +3 (integrity monitoring RAIM FDE, RTS
  fixed-interval smoothing, coverage path planning), propulsion +2
  (cold-gas RCS thruster, rocket turbopump), systems-engineering-safety
  +1 (MSG-3 maintenance decision logic), vehicle-design +1 (canard
  sizing), cross-cutting +1 (cross-correlation numerics utility) = 8
  leaves in the 32-families. flight-mechanics: re-probed and documented
  as provably saturated - every candidate checked this wave is claimed
  by an existing sibling (V-n / maneuver envelope = flight-test-
  operations load-factor-envelope owns the V-n diagram computation;
  dutch-roll = lateral-directional-stability; maneuver-point =
  longitudinal-stability; time-to-climb = climb-performance;
  accelerate-stop / balanced-field = flight-test-operations
  accelerate-stop-distance plus takeoff-performance; stick-free neutral
  point rejected as an overlap risk on longitudinal-stability), so no
  FM slot was spent (brief allows documented saturation + shift to the
  next smallest family). Slots then went to the 33-count families:
  space-systems +2, avionics +1 (new surveillance pack). Largest
  (FTO/MQ/STRUCT 34-count) untouched, per doctrine.

- FAMILY SPREAD after wave (393 -> 404): gnc-autonomy 32 -> 35,
  propulsion 32 -> 34, systems-engineering-safety 32 -> 33,
  vehicle-design 32 -> 33, cross-cutting 32 -> 33, space-systems 33 ->
  35, avionics 33 -> 34 (new surveillance pack); flight-mechanics 32,
  aerodynamics 33, flight-test-operations 34, manufacturing-quality 34,
  structures 34 unchanged. 85 packs (84 + surveillance).

- STANDARDS-MAP +3 (additive at prep, field-guide format): rtca-do-229
  (RAIM MOPS), rtca-do-185 (TCAS II MOPS), msg-3 (ATA MSG-3), all
  gated: true. Manifest regenerated at close (416 SKILL.md, 28
  standards); no-verbatim and content-policy sweeps green on the new
  leaves.

- CORPUS 800 -> 822 tasks (22 new, 11 fragments merged via
  state/wave29-merge-corpus.py then deleted, 0 on disk), grep
  verified. 7 family routers updated parent-side (one table row + one
  routing-guidance bullet per new leaf: cross-cutting, gnc-autonomy,
  propulsion, systems-engineering-safety, vehicle-design,
  space-systems, avionics), all router descriptions <= 1024 chars
  verified via wave16-router-desc-len.py PASS (all 12 families;
  propulsion 1024 and flight-test-operations 1022 remain the maxes,
  unchanged). Router parity check PASS for all 12 families (rows ==
  leaves: 33/33 aero, 34/34 avionics, 33/33 CC, 32/32 FM, 34/34 FTO,
  35/35 GNC, 34/34 MQ, 34/34 PROP, 35/35 space, 34/34 structures,
  33/33 SES, 33/33 VD). Ledger header updated 393 -> 404 (rows 1-404
  contiguous, no duplicates). Visuals regenerated via make visuals
  (numbers only; visuals-check PASS 19 artifacts fresh, 404 leaves /
  85 packs); manifest-check PASS zero diff; stale-number-guard PASS
  after the docs number refresh.

- HIT@1 NO-TASK-STEALING: gate 5 re-run after the merge returned
  822/822 PASS with ZERO pre-existing tasks stolen (by construction:
  every corpus task top1 == expected skill). Specs carried distinctive
  hyphenated tokens per the sibling fences (raim leaf avoids
  pseudorange-fix and DOP tokens; rts avoids filter-design and
  flight-test smoothing tokens; coverage avoids Dubins and midcourse
  tokens; spacecraft battery avoids traction/eVTOL and solar-array
  tokens; plane change avoids Hohmann coplanar and budget tokens; tcas
  avoids navaid, RNP/ANP, and FMS route tokens; canard avoids tail /
  empennage and neutral-point tokens; msg3 avoids in-service safety
  assessment and FTA/FMEA tokens). No reword of any pre-existing corpus
  task was needed this wave.

- GATES FRESH at rest HEAD 8f1fa670: make validate 5/5 (822/822 Hit@1
  deterministic offline), make attest 3/3, make completeness ALL
  REQUIRED PASS, make value-delta PASS (10/10 >= 0.2), visuals-check
  PASS (19 artifacts fresh), manifest-check PASS, router descs <=
  1024, em dashes 0 in skills/, stale-number-guard PASS, tree clean.
  Pre-push hook re-ran the full gate battery and verified before the
  private push (reported all gates green, package smoke PASS).

- Push PRIVATE via the origin arjun token (identity verified via the
  API: login == arjun-0077) fast-forward only 512b16a8..8f1fa670,
  ls-remote verified remote main == 8f1fa670 == HEAD, no Ashforde
  token on the private repo, no visibility flip. publish-public.sh
  sanctioned sync: gates green inside the export, leaf-count guard
  (404 >= 393) passed, pushed 037e53c8 to ashfordeOU/aero-agent-skills
  (normal fast-forward, no force), verified 404 skills / 85 packs / 12
  families, About refreshed from the mirror post-push (fix eec11e34
  held). GitHub CI: attest run 33789668500 and release-on-milestone
  run 33789668506 both SUCCESS at close-out time.

- SPEC DEVIATIONS / disclosures:
  1. rts-smoother spec: the noiseless-ramp identity anchor was
     mathematically wrong at q = 0.1 (with process noise the smoothed
     velocity on a perfect ramp shows small shrinkage, not 1e-9
     exactness). Caught during the build by the builder's own probe;
     ops steered once: the 1e-9 identity now runs at q = 0.0 (exact CV
     model) and the main worked example keeps q = 0.1 with the stated
     anchors. The builder recovered without re-dispatch.
  2. gnss-raim-fde spec: the original worked bias case (45 m on sat 2)
     did not clear the detection threshold and the FDE worst-sat case
     tied between two symmetric satellites; ops re-tuned the example
     during prep to a 200 m bias on sat 1 (margin 15.3 percent on the
     normalized residual) before dispatch. Builder anchors matched.
  3. wave-29 corpus merge deleted the 11 fragments in a second,
     separate explicit-path commit (7ee73e4b) after the close commit
     (b14c4d1b) because the merge helper unlinks files that were
     tracked at HEAD; both units are clean and the tree is clean at
     close. (Wave-28 merged fragment files that had not been committed
     separately; wave-29 builders committed each fragment inside their
     leaf commit, so deletion showed as tracked-file removal.)
  4. The cross-correlation worked example convention and the
     autocorrelation symmetry numbers were tightened during prep to
     remove ambiguity (lag sign convention stated in the spec).
  5. No builder died this wave (11/11). One steer total (rts-smoother).
     Dispatch lesson: three batches (4 + 4 + 3) from prep commit
     8d25c0ec; fan-out wall time roughly 17:41-18:06 UTC. Specs with
     precomputed stdlib anchors (RAIM HPL 44.5 m, RTS smoothed
     positions, turbopump S 4.123, cold-gas total impulse 5057.7 Ns,
     GTO combined 1.832 km/s, TCAS tau_mod values) kept verification
     mechanical; every builder smoke reproduced its spec anchors.

- Next: CEO P5.2 WAVE-29 audit >= 9.5 -> WAVE-30.
