# Wave-30 state notes

- 2026-09-03 WAVE-30 close: 12/12 planned leaves landed (founder mandate
  >=10 MET +2), close-out commits at HEAD 2eae5fd2 on main (private
  arjun-0077/aero-agent-skills, pushed via the arjun origin token and
  ls-remote verified remote main == HEAD). Full brief:
  ops/automation/wave30-brief.md (0397030d). Prep commit 079673a5
  (builder kit + 12 specs + merge helper + 2 standards-map additions:
  far-29, rtca-do-260b). Close commits: 7764e998 (corpus merge + routers +
  ratings header + visuals/manifest refresh), 2eae5fd2 (fragment deletion,
  wave-29 precedent 7ee73e4b).

- LEAVES (404 -> 416, rate-at-creation 9.5 in-turn, rows 405-416 appended
  by each builder at creation, no duplicates, header updated 404 -> 416 at
  close):
  flight-mechanics/performance/rotorcraft-hover-performance (2e277638),
  flight-mechanics/performance/rotorcraft-forward-flight-performance
  (3def8a02), aerodynamics/high-speed/aerodynamic-heating (28178fbf),
  aerodynamics/boundary-layer/boundary-layer-transition (38353b94),
  avionics/surveillance/ads-b-surveillance (144626e6, 2nd leaf in the
  wave-29 surveillance pack), structures/composites/composite-repair
  (2a8796e1), structures/thermal-structures/thermal-buckling (ea162787),
  structures/loads/landing-ground-loads (3b386b2e),
  cross-cutting/numerics/descriptive-statistics (1f0abf8b),
  manufacturing-quality/assembly/ewis-installation-quality (43b26539),
  space-systems/orbit-mechanics/three-body-libration (dc5d05c6),
  gnc-autonomy/control/adaptive-control (79e4c5f7).
  Every leaf shipped the per-skill completeness standard (SKILL.md +
  stdlib logic + offline unittest + eval fragment + value-delta JSON +
  ledger row). All 12 contract tests re-run by ops at HEAD: PASS (unittest
  counts 32-35 per leaf, 402 methods total). All 24 new corpus tasks Hit@1
  to their own leaf.

- SMALLEST-FIRST honored with a domain finding: flight-mechanics (32) was
  re-probed FIRST with a fresh receipt (wave-30): the wave-29 saturation
  list still holds at HEAD - V-n / maneuver envelope = flight-test-
  operations load-factor-envelope (grep-confirmed this wave), dutch roll =
  lateral-directional-stability, maneuver point / stick-free neutral point
  = longitudinal-stability (and stability-derivatives-avl, phugoid,
  short-period, trim-analysis all match neutral-point tokens),
  time-to-climb = climb-performance + flight-test-operations
  climb-performance-flight-test, accelerate-stop / balanced field =
  flight-test-operations accelerate-stop-distance. FIXED-WING FM topics are
  provably saturated. The re-probe found ONE genuine non-overlapping gap:
  the rotorcraft domain is entirely absent from the library (every FM leaf
  is fixed-wing; nothing computes rotor induced power or hover power). Two
  FM slots were spent there (hover momentum theory, forward-flight Glauert
  power breakdown) with far-29 added to the standards map as the rotorcraft
  certification-basis id. Slots then went to the four 33-count families:
  aerodynamics +2 (stagnation heating, transition location), cross-cutting
  +1 (descriptive statistics - the numerics pack lacked a sample-summary
  leaf), vehicle-design and systems-engineering-safety re-probed and
  documented dense/saturated (no clean non-duplicate gap found; VD and SES
  unchanged at 33). The five 34-count families: structures +3 (scarf
  repair, thermal buckling, landing ground loads - all clean gaps),
  avionics +1 (ADS-B in the surveillance pack), manufacturing-quality +1
  (EWIS installation checks - the assembly pack had only fasteners),
  flight-test-operations re-probed and documented dense/saturated
  (untouched, 34), propulsion assessed after the wave-29 +2 and documented
  dense (untouched, 34). Largest families probed last: space-systems +1
  (CR3BP libration points - the orbit-mechanics pack had no three-body
  content; gravity-assist-swingby is patched-conic and does not overlap),
  gnc-autonomy +1 (model-reference adaptive control - the control pack had
  no adaptive/robust leaf).

- FAMILY SPREAD after wave (404 -> 416): flight-mechanics 32 -> 34,
  aerodynamics 33 -> 35, cross-cutting 33 -> 34, avionics 34 -> 35,
  structures 34 -> 37, manufacturing-quality 34 -> 35, space-systems 35 ->
  36, gnc-autonomy 35 -> 36; vehicle-design 33, flight-test-operations 34,
  propulsion 34, systems-engineering-safety 33 unchanged. 85 packs (no new
  pack this wave; surveillance reached 2 leaves).

- STANDARDS-MAP +2 (additive at prep, field-guide format): far-29 (14 CFR
  Part 29 rotorcraft, gated false), rtca-do-260b (ADS-B 1090ES MOPS, gated
  true). Manifest regenerated at close (428 SKILL.md, 30 standards);
  no-verbatim and content-policy sweeps green on the new leaves.

- CORPUS 822 -> 846 tasks (24 new, 12 fragments merged via
  state/wave30-merge-corpus.py then deleted in a separate explicit-path
  commit, 0 on disk), grep verified. 8 family routers updated parent-side
  (one table row + one routing-guidance bullet per new leaf:
  flight-mechanics, aerodynamics, avionics, structures, cross-cutting,
  manufacturing-quality, space-systems, gnc-autonomy), router descriptions
  unchanged and verified <= 1024 chars via wave16-router-desc-len.py PASS
  (all 12 families; propulsion 1024 and flight-test-operations 1022 remain
  the maxes). Router parity check PASS for all 12 families (rows == leaves:
  35/35 aero, 35/35 avionics, 34/34 CC, 34/34 FM, 34/34 FTO, 36/36 GNC,
  35/35 MQ, 34/34 PROP, 36/36 space, 37/37 structures, 33/33 SES, 33/33
  VD). Ledger header updated 404 -> 416 (rows 1-416 contiguous, no
  duplicates). Visuals regenerated via make visuals (416 leaves / 85
  packs); visuals-check PASS 19 artifacts fresh; manifest-check PASS zero
  diff; metrics.json verified (416 leaves, 12 families, 85 packs, 846
  corpus tasks, 30 standards); stale-number-guard PASS after the docs
  number refresh.

- HIT@1 NO-TASK-STEALING: gate 5 re-run after the merge returned 846/846
  PASS with ZERO pre-existing tasks stolen (every corpus task top1 ==
  expected skill). By construction: specs carried distinctive hyphenated
  tokens per the sibling fences (rotorcraft leaves avoid all fixed-wing
  performance tokens; aerodynamic-heating avoids newtonian/shock/wave-drag
  tokens; boundary-layer-transition avoids flat-plate thickness and
  skin-friction tokens; ads-b avoids TCAS tau/DMOD and GNSS RAIM tokens;
  composite-repair avoids volkersen/bearing/dcb tokens; thermal-buckling
  avoids mechanical plate-buckling k-table and bimetallic tokens;
  landing-ground-loads avoids gust/maneuver and strut/tire tokens;
  descriptive-statistics avoids hypothesis/distribution/control-chart
  tokens; ewis avoids fastener and databus tokens; three-body-libration
  avoids swingby and transfer-maneuver tokens; adaptive-control avoids
  pid/root-locus/lqr tokens). No reword of any pre-existing corpus task was
  needed this wave. Note: space-systems entry-descent-landing mentions
  Sutton-Graves convective heating in its routing bullet, but the w30
  aerodynamic-heating tasks still routed 1.0 to the new aero leaf (score
  18-20.5 vs the EDL row) - no steal, no reword required.

- GATES FRESH at rest HEAD 2eae5fd2: make validate 5/5 (846/846 Hit@1
  deterministic offline), make attest 3/3, make completeness ALL REQUIRED
  PASS, make value-delta PASS (10/10 >= 0.2), visuals-check PASS (19
  artifacts fresh), manifest-check PASS zero diff, router descs <= 1024,
  em dashes 0 in skills/, stale-number-guard PASS, tree clean.

- Push PRIVATE via the origin arjun token, fast-forward only
  0397030d..HEAD, ls-remote verified remote main == HEAD, no Ashforde token
  on the private repo, no visibility flip. publish-public.sh sanctioned
  sync + public HEAD verify + GitHub CI attest SUCCESS at close-out time
  (details below).

- SPEC DEVIATIONS / disclosures:
  1. Concurrent non-builder commits landed on main during the wave from
     the environment's release/docs automation (release version sync
     f8974068, release visual refresh 6bf5c737, docs hyperlinks 857589c4,
     visuals refresh 007d2e6d, release-on-milestone fix 54385736). All are
     local-only (remote stayed at the wave-30 brief until the close push),
     all fast-forward below the wave commits, none touched
     eval/hit1-corpus.yaml, standards-map.yaml, Makefile, or scripts/.
     6bf5c737 swept an in-flight copy of the aerodynamic-heating logic into
     packages/ mid-build (wave-16 class race); the close `make visuals`
     manifest regeneration overwrote it with the final leaf content and
     manifest-check is zero-diff at HEAD. A stray untracked temp
     (ops/tmp_metrics_report.py) left by that tooling was removed at close
     so the tree is clean.
  2. adaptive-control builder hit one float-artifact assertion failure
     (assertEqual on -0.3) and fixed it with assertAlmostEqual; no spec
     deviation, no steer needed. No builder died (12/12). Zero steers this
     wave.
  3. FM fixed-wing saturation was re-documented with the fresh wave-30
     grep receipt (list above) per the brief's requirement; the FM slots
     were spent on the rotorcraft gap, which is a genuine addition to the
     domain (first non-fixed-wing flight-mechanics content) rather than a
     duplicate.
  4. Dispatch was rolling (not fixed batches): 4 + 3 + 3 + 1 + 1 as slots
     freed, cap 4 concurrent held throughout. Fan-out wall time roughly
     18:47-19:05 UTC. Prep-to-close completed 18:44-19:14 UTC, well inside
     the build daylight; the 19:30 pre-quiet spawn cutoff was not
     approached.

- Next: CEO P5.2 WAVE-30 audit >= 9.5 -> WAVE-31.
