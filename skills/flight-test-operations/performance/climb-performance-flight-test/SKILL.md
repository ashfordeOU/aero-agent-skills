---
name: climb-performance-flight-test
description: "Use when you must run a climb performance flight test on a fixed-wing aircraft: measure the rate of climb in feet per minute from the pressure altitude change over a timed steady climb segment, correct the measured rate of climb for the test weight and the density altitude to the reference condition, convert the pressure altitude rate to the geometric rate with the outside air temperature, determine the service ceiling and the absolute ceiling where the best rate of climb decays to the threshold, integrate the time to climb between altitudes, and check the climb gradient in percent against the certification requirement. Produces the corrected rate of climb, the ceiling altitudes, the time to climb, and the gradient margin that gate the climb test assessment. Trigger: climb flight test, rate of climb, pressure altitude, service ceiling, climb gradient, time to climb, steady climb."
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
  subdomain: performance
  tags: [climb-flight-test, rate-of-climb, pressure-altitude, service-ceiling, climb-gradient, time-to-climb, steady-climb, ceiling-determination]
  version: 0.1.0
  author: AeroSkills
---

# Climb Performance Flight Test (flight-test-operations/performance/climb-performance-flight-test)

Use when the task is climb performance flight testing: the rate of
climb measurement from timed steady climb segments, the weight and
density corrections of the measured rate, the service and absolute
ceiling determination, the time to climb, and the climb gradient
checks against the certification requirement.

## Domain quick reference

- Test technique: the sawtooth climb, a series of timed climb segments
  over measured pressure altitude blocks at a constant indicated
  airspeed and a fixed power setting, with the outside air temperature
  recorded per block; or a continuous climb sampled at altitude steps.
  The airplane is trimmed, the configuration is fixed, and the segment
  is straight.
- rate_of_climb_from_pressure_altitude: ROC = (h2 - h1) / t * 60 in
  ft/min from the pressure altitude change over the segment time.
  Worked: 2000 ft gained in 60 s gives 2000 ft/min.
- geometric_roc_from_pressure_roc: h_geo_dot = h_p_dot *
  T_amb / T_ISA(pressure altitude); at the same pressure the geometric
  altitude rate exceeds the pressure altitude rate by the ambient over
  ISA temperature ratio. Worked: 2000 ft/min at 10000 ft pressure
  altitude with OAT 15 C (ISA there is -4.8 C) gives 2147.7 ft/min.
- density_altitude_ft: sigma = delta(pressure altitude) * T0 / T_amb,
  then the altitude where the ISA density ratio equals sigma. Worked:
  10000 ft pressure altitude with OAT 15 C gives a 12248 ft density
  altitude; on the ISA day at 10000 ft (OAT -4.8 C) the density
  altitude equals the pressure altitude.
- Corrections of the measured rate: the weight correction
  weight_corrected_roc, ROC_ref = ROC_meas * W_test / W_ref, the
  specific excess power per unit weight scaling at constant true
  airspeed, the first order form valid when the drag is a small
  fraction of the thrust; the density correction
  density_corrected_roc, ROC_std = ROC_meas *
  (sigma_test / sigma_std)^(lapse_exp - 0.5), from the thrust lapse
  with sigma^lapse_exp and the true airspeed with sigma^-0.5 at
  constant indicated airspeed. Worked: 2000 ft/min at W_test 20500 lbf
  to W_ref 20000 lbf gives 2050 ft/min; sigma 0.9 with the 0.7 lapse
  exponent gives 1958.3 ft/min; the combined correction gives
  2007.3 ft/min.
- Excess power model for planning: CL = W / (0.5 * rho0 * sigma * V^2 *
  S), CD = cd0 + k * CL^2, D = 0.5 * rho0 * sigma * V^2 * S * CD, T =
  T0 * sigma^0.7, ROC = (T - D) * V / W, climb_gradient_pct = 100 *
  (T - D) / W, the small angle form of the excess thrust over weight.
  Worked at sea level, 400 ft/s, W 20000 lbf, S 320 ft^2, cd0 0.022,
  k 0.0530, T0 6500 lbf: CL 0.329, CD 0.0277, D 1687 lbf, ROC
  5775 ft/min, gradient 24.1 percent.
- Best rate of climb: best_rate_of_climb_fpm scans the true airspeed
  band at the test density and returns the maximum rate and the speed
  that achieves it. Worked for the synthetic light jet: 6289 ft/min at
  516.8 ft/s (306 kt) at sea level, 5179 ft/min at 10000 ft, 4128
  ft/min at 20000 ft.
- Ceilings: the service ceiling is the altitude where the best rate of
  climb decays to the threshold, 100 ft/min for jet aircraft in common
  usage, and the absolute ceiling is where it decays to zero. Worked:
  56354 ft service ceiling and 57189 ft absolute ceiling; a 500 ft/min
  threshold lowers the service ceiling to 52980 ft.
- Time to climb: time_to_climb_min integrates dt = dh / ROC(h) over
  the best rate schedule with the trapezoid rule. Worked: 6.69 min
  from sea level to 30000 ft for the synthetic light jet (planning
  model only, the measured data drive the certification values).
- Gradient checks: gradient_from_roc gives the gradient from the
  measured rate and the true airspeed, and gradient_margin_pct the
  margin against the requirement. Worked at 10000 ft at the best rate
  speed with one of two engines inoperative: 2.70 percent, a margin of
  +0.30 percent against the 2.4 percent takeoff climb gradient
  requirement for a two-engine transport aeroplane (FAR-25.121
  summary, reference-only; verify against the current regulation).
- Model caveat: the parabolic polar omits the compressibility drag
  rise, so predicted rates and ceilings run optimistic at high
  altitude; the flight test measures the actual values and the
  corrected measured data gate the assessment.

## Workflow

1. Fly the sawtooth or continuous climb segments at the test
   configuration, recording pressure altitude, time, OAT, indicated
   airspeed, and weight per segment.
2. Compute the measured rate of climb with
   rate_of_climb_from_pressure_altitude from the pressure altitude
   change and the segment time.
3. Convert the pressure altitude rate to the geometric rate with
   geometric_roc_from_pressure_roc using the OAT and the segment
   pressure altitude.
4. Reduce each segment to the reference condition with
   corrected_rate_of_climb: weight_corrected_roc for the test weight
   and density_corrected_roc for the density altitude, using
   density_altitude_ft for the standard day reference.
5. Build the corrected rate of climb versus density altitude curve and
   locate the best rate speed with best_rate_of_climb_fpm per altitude
   block.
6. Determine the ceilings with service_ceiling_ft at the 100 ft/min
   threshold and absolute_ceiling_ft where the rate decays to zero,
   and the time to climb with time_to_climb_min.
7. Check the climb gradient with climb_gradient_pct and
   gradient_from_roc against the certification requirement, reporting
   the margin with gradient_margin_pct.
8. Report the corrected rate of climb, the ceiling altitudes, the time
   to climb, and the gradient margin for the climb test assessment.

## Pitfalls

- Routing analytical climb questions here: computing the rate of climb
  from excess power without flight test data, service ceiling from a
  drag polar alone, and time to climb estimates belong to
  flight-mechanics/performance/climb-performance; this leaf is the
  flight test side: measurement from timed segments, corrections, and
  ceilings from the corrected data.
- Routing engine test questions here: engine systems checks, fuel
  flow, EGT margins, and engine thrust determination belong to
  engine-flight-test; the climb test consumes thrust, it does not
  determine the engine limits.
- Routing segment distance questions here: takeoff field length and
  the takeoff path segments belong to takeoff-distance-determination,
  landing distance and the approach climb segment to
  landing-distance-determination, and unpowered descent to
  glide-flight-test; this leaf covers the steady powered climb.
- Confusing the pressure altitude rate with the geometric rate: the
  temperature correction matters, 7 percent at 10000 ft with OAT 15 C
  in the worked case.
- Forgetting the weight and density corrections before ceiling
  determination: the measured rate at test weight and density does not
  give the reference ceilings directly.
- Mixing the ceiling definitions: the service ceiling threshold is
  commonly 100 ft/min for jets and differs for propeller aircraft;
  make the threshold explicit in service_ceiling_ft.
- Treating the planning model as the measured result: the parabolic
  polar without compressibility over-predicts the high altitude rate,
  so the measured and corrected data gate the assessment, not the
  model.
- Forming the gradient from the calibrated airspeed: the small angle
  form needs the true airspeed at the test density altitude.
- A zero or negative measured rate is not a climb: the segment must
  gain pressure altitude, and the time to climb integration requires a
  positive rate throughout the band.

## Behavior contract (gate 3)

The climb measurement, correction, ceiling, and gradient logic is
exercised by the gate 3 contract test:
scripts/test_climb_performance_flight_test.py against
scripts/climb_performance_flight_test_logic.py (stdlib unittest,
offline). Run:
`python3 scripts/test_climb_performance_flight_test.py`

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; climb performance
  flight testing is common methodology in the FAR 25.101 general
  performance, 25.115 climb, 25.119 landing climb, and 25.121
  one-engine-inoperative climb context, summary-only per
  standards-map.yaml. Requirement values stated here are reference
  summaries, verify against the current regulation text.
- compliance: STANDARDS-REF, gated: false.
