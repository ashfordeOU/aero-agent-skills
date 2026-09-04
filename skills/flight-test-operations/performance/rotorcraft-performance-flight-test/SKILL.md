---
name: rotorcraft-performance-flight-test
description: "Use when you must reduce a rotorcraft performance flight test from measured data: convert measured main rotor torque and rotor speed into shaft power, compute the measured figure of merit from the ideal induced power and the measured power, correct measured hover power to a reference weight and density altitude with the induced and profile fraction split, correct a measured vertical rate of climb for the test weight, reduce hover power-required points measured across density altitudes to a hover ceiling against the available power, and check the test day against the flight manual limits. Produces the measured power, measured figure of merit, corrected power, corrected vertical rate of climb, the OGE and IGE hover ceiling altitudes, and the test verdict that gate the flight test report. Trigger: rotorcraft-performance-flight-test, rotorcraft-hover-flight-test, measured-figure-of-merit, torque-to-power, hover-ceiling-determination, weight-density-correction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [rotorcraft-performance-flight-test, rotorcraft-hover-flight-test, measured-figure-of-merit, torque-to-power, hover-ceiling-determination, weight-density-correction]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rotorcraft Performance Flight Test (flight-test-operations/performance/rotorcraft-performance-flight-test)

Use when the task is reducing a rotorcraft performance flight test
from MEASURED data: hover power-required built from measured main
rotor torque and rotor speed, the measured figure of merit, the
weight and density correction of the measured hover power, the
weight correction of a measured vertical rate of climb, the hover
ceiling reduced from measured power-required points, and the test
day checked against the flight manual torque limit. Every input is a
flight test measurement: torque, rotor speed, gross weight, density,
altitude. This leaf is the measured-data reduction counterpart to
the flight-mechanics rotorcraft performance leaves, which own the
analytic models computed from geometry and weight.

## Domain quick reference

- Shaft power from the torque measurement:
  shaft_power_from_torque: P = Q * omega, the measured main rotor
  torque (Nm) at the measured rotor speed (rad/s). Worked: 14,815 Nm
  at 27 rad/s gives 400,005 W.
- Ideal induced power for the FM numerator:
  ideal_induced_power: P_ideal = T * sqrt(T / (2 * rho * A)) for the
  rotor disk area A, used only to normalize the measured power.
  Worked at the reference hover condition (21,574.63 N at rho 1.225
  over 78.54 m2): 228,448 W.
- Measured figure of merit: measured_figure_of_merit: FM =
  P_ideal / P_measured. A physical measurement has FM <= 1.0; the
  function rejects measured power at or below zero and any ideal
  power above the measured power. Worked: 228,448 / 400,005 = 0.5711.
- Weight and density correction of measured hover power:
  power_correction_weight_density: P_corr = P_meas * [ f_i *
  (W_ref/W_meas)^1.5 * sqrt(rho_meas/rho_ref) + (1 - f_i) *
  (rho_ref/rho_meas) ], with f_i the induced power fraction
  (default 0.6). The induced fraction scales with the ideal-rotor
  result W^1.5 / sqrt(rho); the profile fraction scales with rho.
  At the reference weight and density the correction returns the
  measured power unchanged. Worked: 400,005 W at 22,500 N and rho
  1.10 corrects to 391,727 W at 21,574.63 N and rho 1.225.
- Vertical rate of climb corrected for test weight:
  corrected_vertical_rate_of_climb: ROC_corr = ROC_meas *
  W_meas / W_ref (excess power scales with weight). A measured
  descent point (negative ROC) is a valid input. Worked: 8.0 m/s at
  22,500 N corrects to 8.34 m/s at 21,574.63 N.
- Hover ceiling from measured power-required points:
  hover_ceiling_altitude linearly interpolates the measured hover
  power-required versus altitude points and returns the altitude
  where the required power equals the available power (the OGE
  ceiling run against the manual OGE available power, the IGE
  ceiling against the ground-effect-incremented value). Returns None
  when the required power at the lowest altitude already exceeds the
  available power (hover not achieved at the lowest test altitude) or
  when the required power at the highest altitude is still below the
  available power; the caller then flags the report that the ceiling
  lies outside the tested band. Worked: required points 395,000 W at
  0 m, 403,000 at 500 m, 411,000 at 1000 m, 419,000 at 1500 m
  against 415,000 W available give a 1250 m ceiling.
- Torque check against the manual limit:
  torque_to_power_check returns {shaft_power_w, within_rated} with
  within_rated True when the shaft power stays at or below
  rated_power * (1 + tolerance), tolerance default 0.05. Worked:
  400,005 W against 450,000 W rated is within_rated True.
- Convenience chain: rotorcraft_performance_test_reduction returns
  exactly {mean_shaft_power_w, measured_figure_of_merit,
  corrected_power_w, within_rated} for a torque point or a list of
  points at a constant rotor speed (or a per-point omega list).
- Units are SI throughout: Nm, rad/s, W, N, kg/m3, m, m/s.
- FAR 29 frames the airworthiness context (reference only); the
  relations above are standard flight-test reduction methodology,
  summary-only, and work only from measured data.

## Workflow

1. Gather the measured test day: torque points at the recorded rotor
   speed, test gross weight, and the density from the test pressure
   altitude and outside air temperature; take the reference weight
   and density and the rated torque from the flight manual.
2. Convert each measured torque point to shaft power with
   shaft_power_from_torque, or run the whole point through
   rotorcraft_performance_test_reduction for the summary dict.
3. Compute the measured figure of merit with
   measured_figure_of_merit at the reference hover condition (the
   reporting basis of the corrected power) over the measured mean
   shaft power.
4. Correct the measured hover power to the reference weight and
   density with power_correction_weight_density and the induced
   fraction split.
5. Correct a measured vertical rate of climb for test weight with
   corrected_vertical_rate_of_climb.
6. Reduce the hover power-required points measured across density
   altitudes to the hover ceiling with hover_ceiling_altitude run
   against the manual available power; treat a None return as a
   report flag for a ceiling outside the tested band.
7. Check the test day against the manual limit with
   torque_to_power_check; a within_rated False verdict sends the
   point to the engine and transmission test team.
8. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_performance_flight_test.py.

## Worked example

Main rotor radius 5.0 m (disk area 78.54 m2), measured torque
14,815 Nm at 27 rad/s, test weight 22,500 N, reference weight
21,574.63 N, rho_meas 1.10 kg/m3, rho_ref 1.225 kg/m3, induced
fraction 0.6. Running the reduction chain on the measured point:

- Mean shaft power: 14,815 * 27 = 400,005 W (within 380,000-420,000
  W).
- Ideal induced power at the reference hover condition (thrust
  21,574.63 N at rho 1.225): 228,448 W (within 210,000-240,000 W).
  At the test-day condition (22,500 N at rho 1.10) the same disk
  gives 256,754 W; the FM and the corrected power are quoted at the
  reference condition so the measurement reduces to one reporting
  basis.
- Measured figure of merit: FM = 228,448 / 400,005 = 0.5711 (within
  0.52-0.62). Evaluating the same measured power against the
  test-day ideal power (256,754 W) would give FM 0.642, outside the
  physical hover band quoted in this report, which is why the
  reference condition is the FM evaluation basis.
- Corrected hover power (f_i = 0.6): 391,727 W (within
  370,000-410,000 W, within 3% of the measured value: the test point
  sits near the reference condition).
- Corrected vertical rate of climb for a measured 8.0 m/s at
  22,500 N to the 21,574.63 N reference: 8.34 m/s (within
  7.5-8.5 m/s).
- Hover ceiling: measured required powers 395,000 W at 0 m,
  403,000 W at 500 m, 411,000 W at 1000 m, 419,000 W at 1500 m
  against 415,000 W available interpolate to a 1250 m ceiling; an
  available power below 395,000 W returns None (hover not achieved at
  the lowest altitude) and one above 419,000 W returns None (ceiling
  above the tested band).
- Torque check against 450,000 W rated with 5% tolerance:
  400,005 W <= 472,500 W, within_rated True.

## Pitfalls

- Mixing the FM evaluation basis: measured figure of merit divides the
  ideal power at the reference condition by the measured power
  (228,448 / 400,005 = 0.5711); evaluating the same measured power
  against the test-day ideal (256,754 W) gives 0.642, outside the
  physical hover band, which is why the reference condition is the
  reporting basis.
- Comparing test-day powers without the weight and density reduction:
  the measured 400,005 W corrects to 391,727 W at the reference (22,500
  N at rho 1.10 reduced to 21,574.63 N at 1.225), and the corrected
  climb rate scales linearly with the weight ratio (8.0 -> 8.34 m/s).
- Interpolating the hover ceiling outside the tested band: an available
  power below the lowest required point (395,000 W) or above the
  highest (419,000 W) returns None - the ceiling is only reported
  inside the measured band (1250 m here).
- Passing an ideal power above the measured power: that is FM > 1 and
  raises ValueError, as do torque < 0, omega <= 0, thrust <= 0,
  rho <= 0, area <= 0, and induced fraction outside [0, 1].
- Feeding mismatched or undersized ceiling data: mismatched ceiling
  lists, fewer than 2 ceiling points, and negative ceiling inputs all
  raise ValueError.
- Reading the torque check without its tolerance: the shaft power is
  within_rated only up to 472,500 W (450,000 W rated at 5%), so a
  torque past that bound reports False.

## Verification

- Confirm shaft_power_from_torque(14815, 27) returns 400,005 W.
- Confirm measured_figure_of_merit(21574.63, 1.225, 78.54, 400005)
  returns 0.5711 and that the ideal power at the test-day condition
  (22,500 N, rho 1.10) exceeds the reference-condition value.
- Confirm power_correction_weight_density returns the measured power
  unchanged when weight and density sit at the reference, and that
  400,005 W corrects to 391,727 W for the worked example (within 3%,
  the test point being near the reference condition).
- Confirm corrected_vertical_rate_of_climb(8.0, 22500, 21574.63)
  returns 8.34 m/s and scales linearly with the weight ratio.
- Confirm hover_ceiling_altitude returns 1250 m for the worked
  points and None for an available power below the lowest required
  point or above the highest required point.
- Confirm torque_to_power_check(14815, 27, 450000) reports
  within_rated True and that a torque pushing the shaft power past
  472,500 W reports False.
- Confirm every non-physical input raises ValueError: torque < 0,
  omega <= 0, thrust <= 0, rho <= 0, area <= 0, measured_power <= 0,
  ideal power above the measured power (FM > 1), weight <= 0,
  induced_fraction outside [0, 1], mismatched ceiling lists, fewer
  than 2 ceiling points, and negative ceiling inputs.
- Confirm determinism: no RNG anywhere, run-to-run identical floats.
- Run the contract test offline: python3
  scripts/test_rotorcraft_performance_flight_test.py (35 tests,
  deterministic, passes in under 20 s).

## Related leaves

- flight-test-operations/performance/climb-performance-flight-test:
  the fixed-wing climb reduction counterpart (its rate of climb
  method uses pressure altitude and airspeed, not rotorcraft weight
  data).
- flight-mechanics/performance/rotorcraft-hover-performance: the
  analytic hover model computed from geometry and weight; this leaf
  reduces the measured flight test data instead.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  the analytic vertical climb model; pair its predicted power with
  the measured reduction here.
- flight-mechanics/performance/rotorcraft-hover-ground-effect: the
  analytic IGE power model behind the IGE ceiling available-power
  increment.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_performance_flight_test.py

The test covers the worked-example anchors (shaft power 400,005 W,
ideal induced power 228,448 W at the reference condition, figure of
merit 0.5711, corrected power 391,727 W, corrected rate of climb
8.34 m/s, within_rated True), the shaft power scaling, the ideal
power scaling identity, the FM unity and rejection cases, the
reference-condition correction identity and the induced fraction
endpoints, the linear weight-ratio scaling of the corrected rate of
climb (descent points allowed), the hover ceiling interpolation with
its endpoint and None cases, the torque limit boundary, the exact
convenience-dict keys, the multi-point mean reduction, and the
ValueError rejection of every non-physical input listed in
Verification.

## Compliance

- FAR 29 frames the airworthiness context; it is referenced, not
  reproduced (no verbatim standard text appears here). The
  relations above are standard rotorcraft flight-test reduction
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
