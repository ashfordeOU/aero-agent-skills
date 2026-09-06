---
name: vmu-determination
description: "Use when you must reduce the takeoff rotation runs of a transport airplane flight test to the minimum unstick speed Vmu in the spirit of the FAR/CS 25.107(b) method, summary-only: classify each measured rotation run against the certified tail-strike rotation limit, correct each liftoff speed from the test weight, altitude, temperature, and flap setting to the reference conditions, and take the minimum corrected speed of the limit-reaching runs as the Vmu verdict with the no-unstick and premature-unstick bracket checks. Produces the corrected run table, the Vmu in m/s and knots, the bracket consistency verdict, and the certification margins against the 1.08 Vmu liftoff constraint and the 1.10 Vs1 rotation floor that gate the V1/VR scheduling. Trigger: minimum unstick speed, vmu determination, rotation limit speed, unstick certification, tail strike rotation limit, takeoff rotation run."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: envelope
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [vmu-determination, minimum-unstick-speed, rotation-limit-speed, unstick-certification, takeoff-rotation-run]
  version: 0.1.0
  author: AeroSkills
---

# Minimum Unstick Speed Determination (flight-test-operations/envelope/vmu-determination)

Use when the task is reducing the measured takeoff rotation runs of a
transport airplane flight test to the minimum unstick speed Vmu in the
spirit of the FAR/CS 25.107(b) method, summary-only: each rotation run
is rated geometrically against the certified tail-strike rotation
limit, each measured liftoff speed is corrected to the reference
takeoff weight, flap, pressure altitude and temperature deviation, and
the
minimum corrected speed of the limit-unstick runs is the Vmu verdict,
bracketed by the no-unstick and premature-unstick run evidence. This
leaf implements the reduction in pure Python, stdlib only, closed form.
It pairs with vmc-determination (this pack) which owns the engine-out
control limit and with v-speeds (this pack) which derives the
stall-multiple speed set; stall-speed-determination (performance)
supplies the reference Vs1 input and takeoff-distance-determination
consumes the rotation speed for the obstacle takeoff distance.

## Domain quick reference

- ISA density ratio at pressure altitude h_p with temperature
  deviation dt_isa: delta = (1 - LAPSE*h_p/T0)**EXP and theta = (T0 -
  LAPSE*h_p + dt_isa)/T0 give sigma = delta/theta, the single-layer
  standard atmosphere. LAPSE = 0.0065 K/m, T0 = 288.15 K, EXP =
  G0/(R_AIR*LAPSE) about 5.2559.
- TAS to CAS: v_cas = v_tas*sqrt(sigma). Calibrated airspeed input
  needs no density correction because CAS already collapses the
  altitude and temperature effect.
- Weight correction at fixed lift coefficient: v_corr = v_cas*
  sqrt(w_ref/w_test), the standard CAS V-speed reduction to the
  reference takeoff weight.
- Configuration normalization through the rotation-limit lift
  coefficient CL(f) = cl_0 + cl_per_deg*f: v_norm = v_cas*
  sqrt(CL(f_test)/CL(f_ref)). More flap gives more lift and a lower
  unstick speed, so a speed measured at a lower flap setting rises
  when normalized up to the reference flap.
- Unstick boundary: the airplane unsticks when the wing lift at the
  achieved rotation angle carries the weight; the certified
  tail-strike rotation limit angle theta_lim is the geometric stop of
  the demonstration. A run that reached the limit and unstuck is the
  Vmu-qualifying class limit-unstick; a run that reached the limit
  without unsticking proves Vmu lies above its speed (no-unstick lower
  bracket); a run that unstuck before the limit proves Vmu lies at or
  below its speed (premature-unstick upper bracket).
- Vmu verdict: vmu_cas is the minimum of the corrected limit-unstick
  run speeds, reported in m/s and in knots (KT2MS = 1852/3600 appears
  only for the knots quote).
- Certification margins, all engines operative: the geometrically
  limited liftoff constraint VLOF >= 1.08*Vmu and the stall-based
  rotation floor Vr >= 1.10*Vs1, where Vs1 is the takeoff-configuration
  reference stall speed from the sibling stall-speed-determination
  leaf. The Vmu verdict gates the V1/VR schedule: when the scheduled
  rotation speed falls below 1.08*Vmu, the schedule must rise to
  vr_required (or V1 must fall) before the certification takeoff is
  consistent with the demonstrated minimum unstick speed.
- Units are SI throughout: m, kg, s, K, m/s; angles in degrees, flap
  in degrees.
- FAR 25.107(b) and CS 25.107(b) frame the unstick demonstration
  method; the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. Fix the reference conditions: the certified tail-strike rotation
   limit theta_lim in deg, the reference takeoff weight w_ref in kg,
   and the reference takeoff flap flap_ref in deg with the
   rotation-limit lift coefficient CL(f) = cl_0 + cl_per_deg*f.
2. Fix the test-day atmosphere and speed basis: the pressure altitude
   h_p and ISA deviation dt_isa of each run, with the density ratio
   from isa_sigma; runs measured as true airspeed are reduced through
   tas_to_cas, calibrated airspeed runs enter directly.
3. Correct each liftoff speed to the reference conditions with
   corrected_run_speed: the weight correction weight_corrected_speed
   to w_ref, then the flap normalization flap_normalized_speed to
   flap_ref (the chain is commutative when the flap factor is 1.0).
4. Classify each rotation run with rotation_run_class against
   theta_lim: no-unstick, limit-unstick (the qualifying class) or
   premature-unstick.
5. Reduce the corrected runs to the Vmu verdict with vmu_verdict:
   vmu_cas is the minimum corrected limit-unstick speed, vmu_knots its
   knots quote, and the bracket consistency check confirms the verdict
   strictly exceeds the fastest no-unstick run and does not exceed the
   slowest premature-unstick run.
6. Check the certification margins with liftoff_margin_108 against the
   scheduled liftoff speed (the 1.08*Vmu constraint, AEO) and the
   1.10*Vs1 rotation stall floor with the reference stall speed from
   the sibling stall-speed-determination leaf.
7. Gate the V1/VR schedule with scheduling_gate: report whether the
   scheduled rotation speed clears the Vmu gate and the stall floor,
   and the rotation speed vr_required that clears the governing floor
   when the schedule falls short.
8. Confirm the deterministic checks with the contract test
   scripts/test_vmu_determination.py.

## Worked example

A transport airplane at reference takeoff weight w_ref = 79000 kg,
certified tail-strike rotation limit theta_lim = 11.0 deg, reference
takeoff flap flap_ref = 15.0 deg with cl_0 = 1.10 and cl_per_deg =
0.020 per deg (CL_lim(15) = 1.400, CL_lim(10) = 1.300). Test day:
pressure altitude 600 m, ISA deviation +12 K. The sibling leaf gives
vs1 = 58.0 m/s; the scheduled rotation speed is vr = 63.9 m/s and the
scheduled liftoff speed is v_lof = 66.4 m/s.

- Atmosphere (step 2): isa_sigma(600, +12) = 0.905430, sqrt(sigma) =
  0.951541; isa_sigma(600, 0) = 0.943654; isa_sigma(0, 0) = 1.000000.
  The warm day at 600 m is about 5% less dense than sea level
  standard. tas_to_cas(64.8, 600, 12) = 61.659846 m/s.
- Rotation run classification (step 4, theta_lim = 11.0 deg): theta
  11.4 unstuck is limit-unstick; 9.8 unstuck is premature-unstick;
  11.0 NOT unstuck is no-unstick; 11.2 and 11.3 unstuck are
  limit-unstick; 11.0 unstuck is limit-unstick (boundary included).
- Per-run corrections and classes (step 3, all runs at flap 15 deg so
  the flap factor is 1.0 in the verdict data):
  - run 1: v 60.8 m/s CAS, 77500 kg, corrected 61.385567 m/s,
    limit-unstick (theta 11.4).
  - run 2: v 62.9 m/s CAS, 79000 kg, corrected 62.900000 m/s,
    premature-unstick (theta 9.8), upper bracket only.
  - run 3: v 59.6 m/s CAS, 79000 kg, corrected 59.600000 m/s,
    no-unstick (limit reached at theta 11.0, no liftoff), lower
    bracket, Vmu lies above this speed.
  - run 4: v 64.8 m/s TRUE airspeed, 78500 kg: TAS to CAS 61.659846
    m/s, then weight correction to 61.855904 m/s, limit-unstick (theta
    11.2). Demonstrates the altitude and temperature correction path
    on the warm-day 600 m run.
  - run 5: v 60.2 m/s CAS, 76500 kg, corrected 61.175752 m/s,
    limit-unstick (theta 11.3).
  The weight factor sqrt(79000/77500) = 1.009631 pulls the heavy-run
  speeds up about 1%.
- Vmu verdict (step 5): vmu_cas = 61.175752 m/s, the minimum of the
  three qualifying corrected speeds (61.385567, 61.855904,
  61.175752), i.e. run 5 exactly; vmu_knots = 118.916149 KCAS.
  Brackets: v_no_unstick_max = 59.6 m/s below the verdict and
  v_premature_min = 62.9 m/s at or above it, so bracket_ok = True: the
  airplane failed to unstick at 59.6 m/s, unstuck at the limit at
  61.176 m/s, and had unstuck prematurely by 62.9 m/s.
- Certification margins (step 6, vs1 = 58.0 m/s):
  - Liftoff constraint (1.08*Vmu, AEO): required_108 = 66.069813 m/s;
    margin = 66.4 - 66.069813 = 0.330187 m/s; ratio v_lof/vmu =
    1.085397 >= 1.08, met = True. The scheduled liftoff clears the
    geometrically limited margin by about a third of a m/s.
  - Rotation stall floor (1.10*Vs1): required = 63.800000 m/s; vr
    63.9 >= 63.8, met = True.
  - Stall proximity: vmu/vs1 = 1.054754, below the 1.10 threshold, the
    regime where the stall guard remains relevant.
- V1/VR gate (step 7): vr 63.9 is BELOW 1.08*Vmu = 66.069813 m/s, so
  vmu_gate_met = False and the verdict is "vmu-gated":
  vr_required = 66.069813 m/s. The Vmu verdict forces the rotation
  speed up by 2.17 m/s (or the V1 schedule down) before the
  certification takeoff is consistent with the demonstrated minimum
  unstick speed.
- Flap normalization path shown separately (step 3): a hypothetical
  run at 10 deg flap with v = 62.9 m/s CAS normalizes to 60.611957 m/s
  at the 15 deg reference (CL 1.300 to 1.400), a 3.6% speed drop from
  the extra flap lift.
- Read-off: this airplane demonstrates Vmu near 118.9 KCAS at MTOW
  conditions. The tail-strike-limited liftoff clears 1.08*Vmu with
  only 0.33 m/s to spare, while the stall-based rotation speed of
  63.9 m/s (124.2 KCAS) sits 2.17 m/s below the 1.08*Vmu gate, so the
  Vmu verdict governs the takeoff speed schedule.

## Verification

- Confirm isa_sigma(600, +12) returns 0.905430 and sits below
  isa_sigma(600, 0) = 0.943654 below 1, and tas_to_cas(64.8, 600, 12)
  returns 61.659846 m/s; the sea level standard call returns the input
  unchanged.
- Confirm weight_corrected_speed(60.8, 77500, 79000) returns
  61.385567 m/s and that weight_corrected_speed(v, w, 4*w) equals
  2*v exactly.
- Confirm flap_normalized_speed(62.9, 10, 15, 1.10, 0.020) returns
  60.611957 m/s and that the 10-to-15-to-10 round trip recovers 62.9
  within 1e-9.
- Confirm corrected_run_speed on the run 4 TAS input returns
  61.855904 m/s, identical to the manual weight and density chain.
- Confirm rotation_run_class returns the three exact class strings and
  includes the boundary (11.0 deg unstuck is limit-unstick).
- Confirm vmu_verdict on the five-run worked data returns
  vmu_cas = 61.175752 m/s, vmu_knots = 118.916149 KCAS and
  bracket_ok = True with the corrected run table above.
- Confirm liftoff_margin_108(61.175752, 66.4) reports required_108 =
  66.069813 m/s, margin 0.330187 m/s, met True, and scheduling_gate
  verdict "vmu-gated" with vr_required = 66.069813 m/s for vr 63.9.
- Confirm every non-physical input raises ValueError: pressure
  altitude outside [0, 11000] m, non-positive ambient temperature,
  non-positive speeds, weights, cl_0, negative flap or cl_per_deg,
  non-positive limit angle, empty or non-qualifying run lists.
- Run the contract test offline: python3
  scripts/test_vmu_determination.py (31 tests, deterministic).

## Related leaves

- flight-test-operations/envelope/vmc-determination: the engine-out
  minimum control AIR speed demonstration, the parallel reduction
  structure in this pack.
- flight-test-operations/envelope/v-speeds: the stall-multiple
  certification speed set; Vr there is a stall multiple, not a
  demonstrated rotation-limit speed.
- flight-test-operations/performance/stall-speed-determination: the
  source of the reference Vs1 used in the 1.10 rotation stall floor.
- flight-test-operations/performance/takeoff-distance-determination:
  consumes the rotation speed for the obstacle takeoff distance.
- vehicle-design/sizing/landing-gear-layout: the tail-strike rotation
  GEOMETRY margin at the aft CG limit; the speed at which the geometry
  limit is reached during rotation runs is this leaf's verdict.
- flight-test-operations/performance/engine-failure-takeoff-flight-test
  and accelerate-stop-distance: the engine-inoperative decision speed
  and stop distance context that this leaf's V1/VR gate feeds.

## Pitfalls

- Reading Vmu off a single limit-unstick run: the verdict is the
  minimum of all qualifying corrected speeds, and it is only bracketed
  evidence when the no-unstick and premature-unstick runs bound it
  (59.6 < 61.176 <= 62.9 in the worked example); an unbracketed
  verdict needs more runs.
- Correcting only the weight: a true-airspeed run measured on a
  warm-day altitude point must first collapse to calibrated airspeed
  through sigma before the weight and flap factors apply (run 4 loses
  about 3 m/s in the TAS to CAS step before the weight pull-up).
- Confusing the flap factor direction: more flap gives more lift and a
  lower unstick speed, so a run measured at 10 deg normalizes DOWN to
  60.612 m/s when the reference is 15 deg; normalizing the wrong way
  inflates the verdict.
- Treating a no-unstick run as a low-speed point: a run that reached
  the limit angle without liftoff proves Vmu lies ABOVE its speed, the
  opposite bracket of a premature-unstick run.
- Gate ordering on the schedule: the Vmu gate (1.08*Vmu) usually binds
  before the stall floor (1.10*Vs1) when vmu/vs1 sits below 1.10 (ratio
  1.054754 in the example), so a schedule that clears the stall floor
  can still be "vmu-gated".
- Deriving Vr from Vs1: this leaf only checks a supplied rotation
  schedule against the floors; the stall-multiple derivation of the
  speed set belongs to the v-speeds sibling.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_vmu_determination.py

The test covers the ISA density ratio and TAS to CAS corrections, the
weight and flap normalization identities and round trips, the full
per-run correction chain, the three rotation run classes with the
boundary case, the five-run worked Vmu verdict (61.175752 m/s,
118.916149 KCAS, bracket_ok True), the bracket removal logic, the
1.08*Vmu liftoff margin and the V1/VR scheduling gate verdicts
("ok", "vmu-gated", "stall-gated", "dual-gated"), and ValueError
rejection of non-physical atmosphere, weight, flap, angle, speed and
run-list inputs. Deterministic, no RNG, no network, 31 tests.

## Compliance

- Standards referenced, not reproduced: FAR 25.107(b) (14 CFR Part 25)
  and CS-25 25.107(b) are the certification method context for the
  minimum unstick speed demonstration; the reduction relations above
  are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
