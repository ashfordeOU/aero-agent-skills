# Wave-33 leaf spec: engine-failure-takeoff-flight-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/engine-failure-takeoff-flight-test/
- Pack: performance. Sibling receipts: accelerate-stop-distance body
  says "no reaction time, no engine-out asymmetry" and "the balanced
  field length V1 is None in this simplified constant-acceleration
  model" - an explicit in-family handoff; takeoff-distance-determination
  reduces all-engine runs only (zero engine-failure/VEF tokens);
  envelope/vmc-determination owns the asymmetric CONTROL boundary (Vmc,
  critical-engine yaw, pedal force), not takeoff distance or V1;
  engine-flight-test = installed thrust of operating engines;
  level-acceleration-test = all-engine excess power;
  climb-performance-flight-test owns the OEI climb-gradient margin
  (this leaf uses ROC only as an input to close the 35-ft takeoff
  segment). Whole-repo balanced.field/VEF/decision.speed has no flight-
  test takeoff owner. This leaf owns the engine-out takeoff reduction
  and balanced-field V1 determination.
- Standards id: far-25 (reference-only) + cs-25 (reference-only; V1/
  field-length certification-test context, paraphrase only - same
  posture as the takeoff sibling). Ledger Standard: far-25.
- Family: flight-test-operations

## Claim

Reduce the one-engine-inoperative (critical-engine) takeoff flight test:
locate the engine-failure point in the measured ground run, add the V1
recognition-time segment, integrate the continued takeoff to the 35-ft
obstacle at the measured engine-out climb rate, and set the decision
speed V1 at the balanced-field intersection where the accelerate-stop
curve equals the continued engine-out takeoff curve. Produces the
engine-failure distance, the recognition distance, the continued
engine-out distance, the balanced-field V1 and distance, and the field
fit verdict.

Does NOT do: all-engine takeoff distance (takeoff-distance-
determination); accelerate-stop distance with no engine-out asymmetry
(accelerate-stop-distance); Vmc/control boundary (vmc-determination);
engine installed thrust (engine-flight-test); OEI climb-gradient
margin demonstration (climb-performance-flight-test).

## Model (implement exactly)

Conventions: measured ground speed v(t) and distance s(t) during the
takeoff run; engine failure speed VEF; recognition time t_rec; V1 the
decision speed; V2 the takeoff safety speed; OEI rate of climb ROC_oei;
35-ft obstacle h_target = 10.668 m (25.113-style closure).
- Engine-failure distance: trapezoid integration of the measured
  ground speed from brake release to the VEF point.
- Recognition distance: s_rec = V1 * t_rec (constant-speed segment at
  the decision speed during the recognition interval).
- Continued climb distance to the obstacle: s_climb = V2 * h_target /
  ROC_oei (constant-speed climb over the obstacle at the OEI rate).
- Engine-out takeoff distance = failure leg + recognition segment +
  continued ground/air legs (document the exact chaining used in the
  summary function).
- Balanced-field V1: the speed where the accelerate-stop distance
  curve ASD(V1) equals the continued engine-out takeoff distance curve
  TOD_N-1(V1); segment-linear intersection; regime flags ASD-limited /
  TOD-limited when no crossing exists in the speed range.
- Ordering checks: V1 >= VEF + a_cont * t_rec (V1 at least the
  failure-plus-recognition speed) and V1 <= V_R (rotation speed).
- Field verdict: margin = runway - balanced distance; fits if >= 0.

Functions (pure stdlib):

- engine_failure_distance(v_samples, t_samples, v_ef) -> meters by
  trapezoid integration to the failure speed (interpolated crossing of
  v_ef in the sample). ValueErrors on empty/invalid arrays.
- recognition_distance(v1_mps, t_rec_s) -> v1 * t_rec.
- continued_climb_distance(v2_mps, roc_oei_mps, h_target_m=10.668) ->
  v2 * h / roc. ValueErrors on non-positive roc/h.
- engine_out_takeoff_distance(...) -> the chained total (document the
  exact signature: failure distance + recognition + continued ground
  segment to V2 + climb segment, or the reduced form used in the
  worked example).
- balanced_field_v1(asd_speeds, asd_dists, tod_speeds, tod_dists) ->
  (v1_mps, dist_m) by segment-linear intersection; return the regime
  flag when no crossing (None v1 with the flag).
- v1_ordering_verdict(v1, v_ef, t_rec, a_cont, v_r) -> dict with the
  V1 >= VEF + a_cont*t_rec and V1 <= V_R checks.
- field_length_verdict(runway_m, dist_m) -> dict {margin_m, fits}.
- engine_failure_takeoff_summary(...) -> dict with all intermediate
  distances, V1, balanced distance, ordering verdicts, field verdict.

## Worked example

ASD curve: speeds 60-80 m/s, distances [1350, 1450, 1560, 1680, 1810]
m. Engine-out TOD curve: [1620, 1600, 1590, 1605, 1630] m. VEF 58 m/s,
recognition 1.0 s, continued acceleration 1.8 m/s2, V_R 80 m/s, runway
1700 m.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- ASD - TOD crosses between 70 and 75 m/s: balanced V1 about 71.43
  m/s at about 1594.3 m.
- V1_min = VEF + a_cont * t_rec = 58 + 1.8 = 59.8 m/s <= 71.43 (pass).
- V1 <= V_R (71.43 <= 80, pass).
- Balanced length about 1594 m vs 1700 m runway: margin about +106 m,
  fits.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty samples; non-positive v_ef/t_rec/roc/h/runway;
  descending or non-monotone distance arrays.
- Balanced-field anchors: v1 about 71.43 m/s, distance about 1594.3 m.
- Ordering verdicts on the worked example: both pass.
- Field verdict: fits with margin about +106 m.
- Regime flags: a TOD curve everywhere above the ASD curve returns
  ASD-limited (no crossing); the reverse returns TOD-limited.
- Monotonicity: longer recognition time raises V1_min (tighter
  ordering); longer runway raises the field margin.
- Determinism: identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-engine-failure-takeoff-flight-test.yaml)

Query 1 (copy verbatim):
  "determine the balanced field decision speed v1 from the intersection of the accelerate stop curve and the continued engine out takeoff distance curve"
  intent: "flight-test-operations; balanced-field V1 from ASD and engine-out TOD intersection"
  expected_skill: "flight-test-operations/performance/engine-failure-takeoff-flight-test"
Query 2 (copy verbatim):
  "reduce the critical engine failure takeoff flight test run from the vef point adding the recognition time segment and the continued climb to the 35 foot obstacle"
  intent: "flight-test-operations; engine-failure takeoff run reduction VEF recognition and 35-ft closure"
  expected_skill: "flight-test-operations/performance/engine-failure-takeoff-flight-test"
Task ids: w33-engine-failure-takeoff-flight-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce the engine-out takeoff
flight test:" and include the outputs in the Claim. First tag:
engine-failure-takeoff-flight-test. Additional tags ONLY:
balanced-field-v1, engine-out-takeoff, vef-recognition,
decision-speed, continued-takeoff, field-length-verdict. NEVER single
generic words (engine, failure, takeoff, v1, distance, field, speed,
climb). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): accelerate stop distance,
reaction time (accelerate-stop-distance owns the all-engine ASD with no
reaction time); ground roll, rotation, all engine (takeoff-distance-
determination); Vmc, critical engine yaw, pedal force (vmc-
determination); climb gradient margin, rate of climb demonstration
(climb-performance-flight-test); installed thrust (engine-flight-test).
The tokens "balanced field", "decision speed V1", "VEF", "engine out
takeoff" are this leaf's own.

Tags: [engine-failure-takeoff-flight-test, balanced-field-v1,
engine-out-takeoff, vef-recognition, decision-speed,
continued-takeoff, field-length-verdict]

Sibling-citation lines for Related leaves:
flight-test-operations/performance/accelerate-stop-distance (the ASD
sibling that defers the balanced-field model),
flight-test-operations/performance/takeoff-distance-determination,
flight-test-operations/envelope/vmc-determination.

Ledger Standard: far-25.
