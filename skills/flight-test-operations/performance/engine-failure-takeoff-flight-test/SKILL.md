---
name: engine-failure-takeoff-flight-test
description: "Use when you must reduce the engine-out takeoff flight test: locate the engine failure point in the measured ground run at the failure speed VEF, add the V1 recognition time segment, integrate the continued takeoff to the 35 ft obstacle at the measured engine out climb rate, and set the decision speed V1 at the balanced field intersection where the stop distance curve equals the continued engine out takeoff distance curve. Produces the engine failure distance, the recognition distance, the continued engine out distance, the balanced field V1 and distance, and the runway fit verdict. Trigger: balanced field, engine out takeoff, decision speed V1, VEF, engine failure flight test, 35 ft obstacle, takeoff field length, field length verdict."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [engine-failure-takeoff-flight-test, balanced-field-v1, engine-out-takeoff, vef-recognition, decision-speed, continued-takeoff, field-length-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# Engine Failure Takeoff Flight Test (flight-test-operations/performance/engine-failure-takeoff-flight-test)

Use when the task is the critical-engine (one-engine-inoperative)
takeoff flight test reduction: locate the engine failure point in the
measured ground run, add the V1 recognition time segment, continue the
takeoff to the 35 ft obstacle at the measured engine-out climb rate,
and set the decision speed V1 at the balanced field intersection of
the stop-distance curve and the continued engine-out takeoff distance
curve. This leaf implements the reduction in pure Python, stdlib only.
It pairs with flight-test-operations/performance/takeoff-distance-
determination for the all-engine runs and with flight-test-operations/
performance/accelerate-stop-distance, whose simplified all-engine
rejected-takeoff model explicitly defers the balanced-field V1 to a
full engine-out model (this leaf).

## Domain quick reference

- Speeds in m/s, accelerations in m/s^2, distances in m. Measured
  ground speed samples v(t) come from the takeoff run; the engine
  failure speed VEF, recognition time t_rec, decision speed V1,
  takeoff safety speed V2 and rotation speed V_R bound the segments.
- Engine failure distance: trapezoid integration of the measured
  ground speed from brake release to the interpolated crossing of VEF
  in the samples (engine_failure_distance). For a constant
  acceleration a the closed form is s_ef = v_ef^2 / (2 a).
- Recognition distance: s_rec = V1 * t_rec, a constant-speed segment
  at the decision speed during the recognition interval.
- Continued climb to the obstacle: s_climb = V2 * h_target / ROC_oei
  with h_target = H_TARGET_M = 10.668 m (35 ft) and ROC_oei the
  measured one-engine-inoperative rate of climb.
- Engine-out takeoff distance chaining (engine_out_takeoff_distance):
  total = failure leg + s_rec + continued ground segment accelerating
  V1 to V2 at a_cont, (v2^2 - v1^2) / (2 * a_cont) + s_climb. The TOD
  curve values used for the balance already embed these legs.
- Balanced-field V1: the speed where the stop-distance curve ASD(V1)
  equals the continued engine-out takeoff distance curve TOD(V1);
  balanced_field_v1 finds the lowest-speed segment-linear intersection
  over the shared speed range. When no crossing exists it returns
  (None, regime): 'asd-limited' when the engine-out TOD curve lies
  everywhere at or above the ASD curve (balance above the tested
  speeds), 'tod-limited' in the reverse case.
- Ordering checks: V1 >= VEF + a_cont * t_rec (v1_min) and V1 <= V_R.
- Field verdict: margin = runway_m - balanced distance; fits when
  margin >= 0. A negative margin is a real outcome (too short).
- FAR-25 (14 CFR Part 25) frames the takeoff field length and V1
  certification-test context; the relations above are standard
  flight-test methodology, summary-only.

## Workflow

1. Reduce the failure leg: with measured speed and time samples,
   engine_failure_distance(v_samples, t_samples, v_ef) integrates the
   ground run to the VEF crossing.
2. Add the recognition segment at the decision speed with
   recognition_distance(v1, t_rec).
3. Close the continued takeoff: continued_climb_distance(v2, roc_oei)
   for the 35 ft closure, or engine_out_takeoff_distance for the full
   chained total (failure + recognition + ground acceleration V1 to V2
   + climb).
4. Determine the balanced decision speed: balanced_field_v1 on the ASD
   and engine-out TOD curves gives (v1, distance), or (None, regime)
   when the curves do not cross in the tested speed range.
5. Run the ordering checks with v1_ordering_verdict (V1 >= VEF +
   a_cont * t_rec and V1 <= V_R) and the runway fit with
   field_length_verdict(runway, distance).
6. Assemble the reduction with engine_failure_takeoff_summary, which
   reports the regime, balanced V1 and distance, v1_min, recognition
   distance, ordering verdicts and field verdict in one dict.
7. Confirm the deterministic checks with the contract test.

## Worked example

ASD curve at 60-80 m/s: [1350, 1450, 1560, 1680, 1810] m. Engine-out
TOD curve: [1620, 1600, 1590, 1605, 1630] m. VEF 58 m/s, recognition
1.0 s, continued acceleration 1.8 m/s^2, V_R 80 m/s, runway 1700 m.
Real module outputs:

- balanced_field_v1 returns V1 = 71.43 m/s (crossing between 70 and
  75 m/s) at 1594.29 m.
- v1_min = VEF + a_cont * t_rec = 59.8 m/s <= 71.43 (pass, margin
  11.63 m/s) and V1 <= V_R (pass, margin 8.57 m/s); ordering pass.
- field_length_verdict: margin = 1700 - 1594.29 = +105.71 m, fits.
- recognition_distance at the balanced V1: 71.43 m.
- engine_failure_takeoff_summary keys: regime, balanced_field_v1_mps,
  balanced_field_distance_m, v1_min_mps, recognition_distance_m,
  ordering_verdict, field_verdict.
- continued_climb_distance(80, 6) = 142.24 m to the 35 ft obstacle at
  a 6 m/s engine-out rate; on a 2 m/s^2 ramp,
  engine_failure_distance to 25 m/s returns 156.25 m, matching
  v_ef^2 / (2 a) = 625 / 4.

## Verification

- Confirm balanced_field_v1(SPEEDS, ASD, SPEEDS, TOD) returns about
  71.43 m/s at about 1594.3 m and that both curves equal the returned
  distance at that speed.
- Confirm the ordering verdict passes and the field verdict fits with
  margin about +106 m against the 1700 m runway.
- Confirm a TOD curve everywhere above the ASD curve returns
  (None, 'asd-limited') and the reverse returns (None, 'tod-limited').
- Confirm the constant-acceleration identity
  engine_failure_distance == v_ef^2 / (2 a) on a linear ramp sample.
- Confirm longer recognition time raises v1_min (tighter ordering) and
  a longer runway raises the field margin.
- Confirm ValueError rejection of empty samples, non-positive
  v_ef/t_rec/roc/h/runway, and descending or non-monotone arrays.
- Confirm run-to-run determinism and the exact summary key set.
- Run the contract test offline: python3
  scripts/test_engine_failure_takeoff_flight_test.py (34 tests).

## Related leaves

- flight-test-operations/performance/accelerate-stop-distance: the ASD
  sibling that defers the balanced-field model (all-engine rejected
  takeoff with no engine-out asymmetry).
- flight-test-operations/performance/takeoff-distance-determination:
  the all-engine takeoff distance runs (no VEF token).
- flight-test-operations/envelope/vmc-determination: the asymmetric
  control boundary (Vmc, critical-engine yaw), not the takeoff
  distance or V1.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_engine_failure_takeoff_flight_test.py

The test covers the trapezoid engine-failure distance and its
closed-form identity on a constant-acceleration ramp, the recognition
segment, the continued climb to the 35 ft obstacle, the chained
engine-out takeoff distance, the balanced-field intersection anchors
(71.43 m/s at 1594.3 m), the ASD-limited and TOD-limited regime flags,
the ordering checks with their boundaries, the runway field verdict
and its margins, the reduction summary key set, determinism, and
ValueError rejection of empty, non-positive and non-monotone inputs.

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25) is US
  government work (public domain) and CS-25 is a free EASA download;
  the V1 and field-length certification-test context is paraphrased,
  summary-only per standards-map.yaml (far-25, cs-25).
- compliance: STANDARDS-REF, gated: false.
