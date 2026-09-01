---
name: flight-loads-survey
description: "Use when you must build a flight test loads survey: calibrate strain gauge load stations against applied ground loads, compute the calibration factor and the measured load at each station, and reduce the load factor versus speed survey points (symmetric and rolling maneuvers) to lift coefficient and load factor for comparison with the predicted loads envelope. Produces the strain calibration factor, per-point measured loads, the survey load factor and lift coefficient, and the maneuver point feasibility verdict that gate the loads survey program. Trigger: loads survey, strain gauge calibration, strain gauge, maneuver point, load factor versus speed, wing bending."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [loads-survey, strain-gauges, load-factor, envelope, flight-test]
  version: 0.1.0
  author: AeroSkills
---

# Flight Loads Survey (flight-test-operations/envelope/flight-loads-survey)

Use when the task is a flight loads survey for a flight test program:
strain gauge calibration, maneuver points, and the load factor versus
speed survey.

## Domain quick reference

- Survey objective: a loads survey measures flight loads (wing
  bending, shear, torsion) with calibrated strain gauge stations and
  compares them against the analytically predicted loads envelope (FAR
  25.301 / CS-25.301 load conditions context). The survey data
  validates the structural load predictions that size the primary
  structure.
- Strain gauge relation: strain epsilon = delta_R / (R * GF), with
  delta_R the gauge resistance change in ohm, R the nominal gauge
  resistance in ohm, and GF the gauge factor (dimensionless, typical
  2.0 to 2.2). Compression gives negative strain.
- Calibration: during the ground calibration the wing or empennage is
  loaded with known applied loads L_i while each gauge records strain
  epsilon_i; the through-origin least squares slope K = sum(L_i *
  epsilon_i) / sum(epsilon_i^2) converts strain to load. The measured
  in-flight load at a station is L = K * (epsilon - epsilon_0) with
  epsilon_0 the pre-flight zero offset.
- Maneuver points: steady symmetric maneuvers (elevator pull-ups and
  pushovers) and rolling maneuvers build load factor at discrete
  survey speeds; each point records the normal acceleration and the
  strain at every station. Measured load factor n = L_meas / W_ref
  with W_ref the reference weight.
- Load factor versus speed survey: at dynamic pressure q = 0.5 * rho *
  V_eas^2 the achieved load factor is n = q * CL / (W/S); the survey
  flies (V, n) points and reduces each to CL = n * (W/S) / q. A point
  is feasible only while CL stays at or below CL_max, otherwise the
  maneuver stalls before reaching the target load factor. Example:
  W/S = 6000 Pa, rho = 1.225 kg/m^3, V = 100 m/s EAS gives q = 6125
  Pa, and CL = 1.8 gives n = 1.8375.

## Workflow

1. Install and verify the strain gauge stations; record the nominal
   resistance R and the gauge factor GF of each gauge.
2. Run the ground calibration: apply the known loads, record the
   strains, and compute the calibration factor per station with
   calibration_factor(loads, strains).
3. Reduce each survey point with measured_load(k, strain,
   zero_strain) and load_factor_from_measured_load(measured,
   reference_weight); keep the point only while its strain lies inside
   the calibrated range (point_in_calibration_range).
4. Convert each speed point with dynamic_pressure(rho, v_eas) and
   lift_coefficient_at_maneuver(load_factor, wing_loading, q), or
   predict the achieved load factor with
   symmetric_maneuver_load_factor(v_eas, rho, wing_loading, cl).
5. Check feasibility against the stall boundary with
   maneuver_point_feasible, compare measured against predicted loads
   with load_error_percent, and gate the survey program on the
   per-point results.

## Pitfalls

- Flying the survey before the ground calibration is complete; the
  strain to load conversion is meaningless without the calibration
  factor and the zero offset.
- Mixing up the two calibration forms: calibration_factor fits the
  through-origin slope K = sum(L * eps) / sum(eps^2); feeding it an
  intercept fit silently changes every measured load.
- Ignoring the zero offset: L = K * epsilon without subtracting the
  pre-flight zero strain shifts every measured load by K * epsilon_0.
- Reporting a strain outside the calibrated range as a load; the
  extrapolation beyond the applied calibration loads is not valid.
- Forgetting that the load factor depends on the reference weight;
  n = L / W_ref with the wrong weight matches neither the V-n diagram
  nor the predicted loads.
- Treating a (V, n) point whose required CL exceeds CL_max as valid;
  the maneuver stalls first and the point does not represent the
  target load factor.
- Taking the calibration factor from a single lightly loaded point;
  the least squares slope needs a spread of loads across the
  calibrated range.
- Passing empty, mismatched, or zero-energy calibration data; the
  module raises ValueError instead of returning a nonsense factor.

## Behavior contract (gate 3)

The strain calibration, load reduction, and load factor versus speed
logic is exercised by the gate 3 contract test:
scripts/test_flight_loads_survey.py against
scripts/flight_loads_survey_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_flight_loads_survey.py

## Compliance

- Standards referenced, not reproduced: the FAR 25 / CS 25 load
  conditions (25.301 context) and the loads survey practice are common
  flight test methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
