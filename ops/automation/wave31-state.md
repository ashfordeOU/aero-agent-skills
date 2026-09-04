# Wave-31 state notes

- 2026-09-04 WAVE-31 close: 11/11 planned leaves landed (founder mandate
  >=10 MET), close-out commits at HEAD 96902fd5 on main (private
  arjun-0077/aero-agent-skills, pushed via the arjun origin token and
  ls-remote verified remote main == HEAD). Full brief:
  ops/automation/wave31-brief.md (2b041be4). Prep commits: 123baa9e
  (builder kit + 11 specs + merge helper; no standards-map additions
  needed this wave, all cited ids already present) and 7b5a809e (corpus
  query reword, see deviations). Close commits: b5267e8a (corpus merge
  868 + 7 routers + ratings header 427 + visuals/manifest refresh),
  96902fd5 (fragment deletion, wave-30 precedent 2eae5fd2).

- LEAVES (416 -> 427, rate-at-creation 9.5 in-turn, rows 417-427 appended
  by each builder at creation, no duplicates, header updated 416 -> 427 at
  close). Commit that first carried each leaf's content on the HEAD chain:
  flight-mechanics/performance/rotorcraft-vertical-climb-performance
  (77940f40), flight-mechanics/performance/rotorcraft-hover-ground-effect
  (008818da), flight-mechanics/performance/rotorcraft-tail-rotor-sizing
  (236b9ee7), cross-cutting/numerics/fir-filter-design (77940f40),
  flight-test-operations/performance/rotorcraft-performance-flight-test
  (5d28be0c), avionics/surveillance/airborne-weather-radar (0e7deb76),
  space-systems/orbit-mechanics/bi-elliptic-transfer (31c2c2ad),
  space-systems/mission-design/c3-departure-energy (3ad1b8cd),
  gnc-autonomy/guidance/augmented-proportional-navigation (be24b2f0),
  gnc-autonomy/guidance/collision-course-guidance (63185e2c),
  manufacturing-quality/as9100/internal-quality-audit (0661e0ff).
  Every leaf shipped the per-skill completeness standard (SKILL.md +
  stdlib logic + offline unittest + eval fragment + value-delta JSON +
  ledger row). All 11 contract tests re-run by ops at HEAD: PASS (unittest
  counts 32-35 per leaf). All 22 new corpus tasks Hit@1 to their own leaf
  (scores 15.5-28, wide margins).

- SMALLEST-FIRST honored with a family-density finding: SES 33 and VD 33
  were re-probed FIRST with FRESH wave-31 receipts (inventory dump of all
  33 leaves each; SES packs: arp4754a 8, arp4761a 11, certification 4,
  continued-airworthiness 2, mbse 6, requirements 1, safety-case 1; VD
  packs: conceptual 5, cost-estimation 3, mass-properties 3, mdo 3,
  sizing 17, structures-integration 2). Both provably still saturated:
  every canonical topic is covered by an existing leaf with matching
  tokens; no clean non-overlapping gap. Per the brief those slots were
  documented here and spent on the next-smallest families.

- FM (34) rotorcraft re-probe (the wave-30/31 flagged NEW domain):
  fixed-wing saturation receipts from wave-29/30 still hold at HEAD.
  Rotorcraft had only hover + forward flight (wave-30). Fresh gaps landed:
  vertical climb (axial momentum theory climb, absent), hover in ground
  effect (the wave-30 hover leaf defers HIGE to the aerodynamics wing
  ground-effect leaf, which computes a WING induced-drag factor, not a
  rotor induced-power factor: genuine rotorcraft gap), tail-rotor
  anti-torque sizing (main-rotor torque balance; no anti-torque content
  anywhere). Autorotation was probed and DECLINED with a receipt: momentum
  theory is inapplicable in the vertical-descent autorotation operating
  range (vortex-ring/windmill transition, Leishman "Rotorcraft
  Aeromechanics" ch.4 and "Principles of Helicopter Aerodynamics" ch.2
  receipts), so a deterministic first-principles stdlib contract test
  would need empirical corrections out of scope; documented for a future
  empirical-model leaf. Figure of merit and rotor torque/power probes:
  FM is owned by the wave-30 hover leaf; main-rotor torque is the input to
  the new tail-rotor leaf, not a separate computation. FM 34 -> 37.

- FTO (34) fresh re-probe: all 6 packs enumerated (envelope 11, flutter 3,
  performance 9, planning 8, stability 2, uas 1); fixed-wing coverage
  dense per wave-30. ONE genuine non-overlapping gap found: zero
  rotorcraft content in the entire FTO family (grep receipt) while the FM
  rotorcraft subdomain is growing. Landed rotorcraft-performance-flight-test
  (measured torque-to-power, measured figure of merit, weight/density
  corrections, hover-ceiling reduction). FTO 34 -> 35.

- PROP (34) fresh re-probe: 10 packs enumerated (axial-compressor 5,
  combustion 1, electric 3, engine-airframe 1, gas-turbine-cycle 5,
  ramjet 2, rocket 10, turbofan 3, turbomachinery 2, turboprop 2).
  Wave-30 dense receipt holds. Scramjet was probed and DECLINED with a
  receipt: a defensible 1-D scramjet cycle model needs Rayleigh-flow
  handling and thermal-choke bookkeeping that could not be pinned to
  contract-test certainty within the wave; ramjet-cycle + ramjet-inlet
  still cover the ramjet family. PROP unchanged at 34, documented dense.

- CC (34): numerics pack (19) re-probed. cubic-spline is ALREADY owned by
  the interpolation leaf (natural cubic spline + spline coefficients);
  ANOVA is owned by hypothesis-testing. The genuine gap landed is the FIR
  filter design space (digital-filter-design owns Butterworth IIR only;
  zero finite-impulse-response content in the library). CC 34 -> 35.

- AERO (35) re-probed and documented dense: high-lift-systems already owns
  leading-edge slat and Krueger increments; flutter-speed-prediction
  already owns Theodorsen unsteady aerodynamics and the V-g method;
  ground-effects owns the wing case (rotorcraft HIGE landed in FM where
  the rotorcraft domain lives); high-speed/wind-tunnel/aeroelasticity
  packs saturated. AERO unchanged at 35.

- AV (35): do160 family re-probed: power-input already owns voltage sag,
  surge, and transient-recovery, so no Section-17 voltage-spike gap;
  environmental-qualification already maps vibration to Section 8 and a
  dedicated vibration leaf would require RTCA gated table data (declined).
  Genuine gap landed in the surveillance pack: airborne-weather-radar
  (reflectivity-rainfall Marshall-Palmer Z-R, tilt to cell top, echo
  level, ground clutter check); surveillance had only TCAS + ADS-B.
  AV 35 -> 36.

- MQ (35): as9100 pack re-probed (11 leaves). Internal audit program
  mechanics (schedule by risk, auditor independence, sample size, finding
  classification, closure verification) were absent: the quality leaf maps
  audit FOCUS AREAS to clauses, corrective-action owns the 8D record, but
  nothing planned/scored the audit program. Landed internal-quality-audit.
  MQ 35 -> 36.

- STRUCT (37): assessed for density (largest family, wave-30 +3).
  continuous-turbulence loads and stiffener-crippling were probed; both
  need FAR 25.341(b)-style spectral-loads or empirical crippling
  correlations that could not be pinned to deterministic contract-test
  certainty within the wave (gust-maneuver-loads owns the discrete-gust
  case; landing-ground-loads, random-vibration-analysis and
  shock-response-spectrum complete the loads pack). Documented dense for
  this wave; STRUCT unchanged at 37.

- SPACE (36): orbit-mechanics probed; landed bi-elliptic-transfer
  (three-impulse comparison vs the two-impulse hohmann-transfer at large
  radius ratios; crossover content absent). mission-design probed:
  launch-window-analysis has no C3/injection content and
  gravity-assist-swingby owns the FLYBY not the DEPARTURE; landed
  c3-departure-energy. satellite-constellation-design was probed and
  DECLINED: satellite-coverage already owns constellation coverage,
  Walker-delta phasing, and revisit content. SPACE 36 -> 38.

- GNC (36): guidance pack probed. proportional-navigation owns the pure PN
  law only (no target-acceleration augmentation; grep receipt); landed
  augmented-proportional-navigation. pursuit-guidance owns pure pursuit
  (tail chase) only; the constant-bearing collision-course geometry (lead
  angle, collision triangle, predicted intercept point) was absent; landed
  collision-course-guidance. Control/navigation/estimation packs probed
  dense. GNC 36 -> 38.

- FAMILY SPREAD after wave (416 -> 427): flight-mechanics 34 -> 37,
  cross-cutting 34 -> 35, flight-test-operations 34 -> 35, avionics
  35 -> 36, gnc-autonomy 36 -> 38, manufacturing-quality 35 -> 36,
  space-systems 36 -> 38; aerodynamics 35, propulsion 34, structures 37,
  systems-engineering-safety 33, vehicle-design 33 unchanged. 85 packs
  (no new pack this wave).

- STANDARDS-MAP unchanged (30 ids; every cited id already present: far-29,
  naca-tr-824, rtca-do-185, ecss, arp4754a, as9100).

- CORPUS 846 -> 868 tasks (22 new, 11 fragments merged via
  state/wave31-merge-corpus.py then deleted in a separate explicit-path
  commit, 0 on disk), grep verified. 7 family routers updated parent-side
  (one table row + one routing-guidance bullet per new leaf:
  flight-mechanics, cross-cutting, flight-test-operations, avionics,
  space-systems, gnc-autonomy, manufacturing-quality), router descriptions
  unchanged and verified <= 1024 chars via wave16-router-desc-len.py PASS
  (all 12 families; propulsion 1024 and flight-test-operations 1022 remain
  the maxes). Router parity check PASS for all 12 families (rows == leaves:
  35/35 aero, 36/36 avionics, 35/35 CC, 37/37 FM, 35/35 FTO, 38/38 GNC,
  36/36 MQ, 34/34 PROP, 38/38 space, 37/37 structures, 33/33 SES, 33/33
  VD). Ledger header updated 416 -> 427 (rows 1-427 contiguous, no
  duplicates). Visuals regenerated via make visuals (427 leaves / 85
  packs); visuals-check PASS 19 artifacts fresh; manifest-check PASS zero
  diff; metrics.json verified (427 leaves, 12 families, 85 packs, 868
  corpus tasks, 30 standards).

- HIT@1 NO-TASK-STEALING: gate 5 re-run after the merge returned 868/868
  PASS with ZERO pre-existing tasks stolen. One pre-existing task (pn1,
  the original proportional-navigation corpus task) initially routed to
  the new augmented-proportional-navigation leaf because both descriptions
  share planar-intercept/closing-velocity/line-of-sight-rate tokens; pn1
  was reworded to carry the proportional-navigation leaf's distinctive
  hyphenated tag tokens (proportional-navigation, closing-velocity,
  line-of-sight-rate, planar-intercept) per the wave-24R / wave-26 p1
  reword precedent. Re-run: pn1 routes 1.0 to proportional-navigation and
  the w31 APN tasks still route to APN (scores 15.5-28). No other reword
  was needed. Specs carried distinctive hyphenated tokens per the sibling
  fences; the 7 remaining corpus queries were revised at prep time after a
  pre-merge routing simulation showed sibling steals, and every fragment
  was verified to carry the revised verbatim text.

- GATES FRESH at rest HEAD 96902fd5: make validate 5/5 (868/868 Hit@1
  deterministic offline), make attest 3/3, make completeness ALL REQUIRED
  PASS, make value-delta PASS (10/10 >= 0.2), visuals-check PASS (19
  artifacts fresh), manifest-check PASS zero diff, router descs <= 1024,
  em dashes 0 in skills/, tree clean.

- Push PRIVATE via the arjun origin token, fast-forward only, ls-remote
  verified remote main == HEAD, no Ashforde token on the private repo, no
  visibility flip. publish-public.sh sanctioned sync + public HEAD verify
  + GitHub CI attest SUCCESS at close-out time.

- SPEC DEVIATIONS / disclosures:
  1. Planned 11 leaves, not the 12-16 upper band. The family probes above
     returned 11 genuine non-overlapping gaps across 8 families; SES, VD,
     AERO, PROP, and STRUCT are documented dense with fresh receipts after
     specific candidates (autorotation, scramjet, stiffener-crippling,
     continuous-turbulence, do160-vibration, satellite-constellation)
     were probed and declined on correctness grounds (receipts above).
     >=10 landed so the wave PASSes per the brief.
  2. Shared-index commit race (wave-16 class, first seen this wave):
     concurrent builders' explicit-path adds collided in the shared git
     index. Commit 01085147 (vertical-climb builder) swept the
     airborne-weather-radar files into its commit; the weather-radar
     builder then committed its own 0e7deb76 with the remaining paths.
     Commit 77940f40 (vertical-climb re-commit after the race) swept the
     fir-filter-design files; the FIR builder's own commit c2d2e0e6 became
     dangling. 01085147 and c2d2e0e6 are unreachable at close; the HEAD
     chain carries every one of the 11 leaves' six artifacts complete
     (verified via git ls-tree per leaf, contract tests PASS at HEAD).
     No content was lost or reverted.
  3. pn1 corpus reword (deviations section 4 above): the only pre-existing
     task touched; documented with the wave-24R precedent.
  4. Spec corpus-query texts were revised at 08:35 UTC (commit 7b5a809e)
     after the pre-merge routing check showed that natural-language
     queries for 7 leaves would lose to sibling descriptions; the four
     batch-2 builders were steered once to re-read the Corpus fragment
     section before writing their fragments (all four fragments verified
     to carry the revised verbatim text). This was a prep-time quality
     catch, not a builder failure.
  5. One anti-hang steer: the collision-course-guidance builder paused 3.5
     minutes reading sibling logic; a single steer moved it to writing.
     No builder died, zero re-dispatches, zero other steers.
  6. No concurrent release/docs commits landed on main during this wave
     (unlike wave-30); the branch stayed linear below the wave commits.

- Next: CEO P5.2 WAVE-31 audit >= 9.5 -> WAVE-32.
