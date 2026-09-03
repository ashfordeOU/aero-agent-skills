---
name: position-error-calibration
description: "Use when you must plan and reduce the airspeed position error calibration (PEC) flight test for a fixed-wing aircraft: schedule the tower fly-by, trailing cone, and GPS ground speed doublet test points across the speed range, compute the calibrated airspeed from the indicated airspeed and the position error correction, reduce the fly-by height error and the reciprocal-heading ground speeds into the position error at each point, fit the piecewise-linear position error correction curve against the indicated airspeed, and produce the PEC table of indicated versus calibrated airspeed. Produces the position error per point, the fitted PEC curve with the residual RMS quality check, the calibrated airspeed set, and the data quality verdict that gate the flight test data reduction. Trigger: position error calibration, airspeed calibration, PEC, calibrated airspeed, tower fly-by, trailing cone, GPS ground speed doublet, position error correction curve."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: planning
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: planning
  tags: [position-error-calibration, airspeed-calibration, pec-table, tower-fly-by, trailing-cone, gps-ground-speed-doublet, calibrated-airspeed, position-error-correction-curve]
  version: 0.1.0
  author: Aero Agent Skills
---

# Position Error Calibration (flight-test-operations/planning/position-error-calibration)

Use when the task is the airspeed position error calibration (PEC)
flight test: planning the test points for the tower fly-by, trailing
cone, and GPS ground speed doublet reference methods, and reducing the
measured runs into the position error correction curve and the PEC
table of indicated versus calibrated airspeed. This leaf implements the
compressible calibrated airspeed relations and the PEC reduction in
pure Python, stdlib only. It pairs with
flight-test-operations/planning/flight-test-data-reduction, whose
channel reduction consumes the PEC table when it computes the corrected
airspeed of each recorded run, with flight-test-operations/envelope/
v-speeds, whose speed rules consume the calibrated airspeed set, and
with flight-test-operations/envelope/high-angle-of-attack-testing,
which runs the separate angle of attack sensor position error method
against its own tower fly-by reference.

## Domain quick reference

- Calibrated airspeed from impact pressure (compressible, ISA sea
  level standard): V_cas = a0 * sqrt(5 * ((q_c/p0 + 1)^(2/7) - 1)),
  with the module constants a0 = 340.294 m/s and p0 = 101325 Pa.
- Impact pressure from calibrated airspeed: q_c = p0 * ((1 + 0.2 *
  (V_cas/a0)^2)^3.5 - 1). The pair is inverse, so V_cas equals V_ias
  exactly when the position error is zero.
- Position error: dVp = V_cas - V_ias; the correction is added to the
  indicated airspeed and is positive when the static source makes the
  airspeed indicator read low.
- Tower fly-by method: the aircraft flies level at a surveyed
  geometric height H_g above the tower while the altimeter at the
  standard setting records the pressure altitude H_p. The height error
  of the static source is dh = H_g - H_p. The static pressure error
  follows the altimeter scale (hydrostatic) relation dp_s = rho * g0 *
  dh, with rho = p(H_p)/(R*T) evaluated at the measured temperature,
  and the same dp_s displaces the impact pressure of the airspeed
  indicator by -dp_s, so V_cas = V_isa(qc(V_ias) + dp_s) with the exact
  compressible airspeed indicator law. Simplified relation used by the
  reduced function: the pass speed is taken at the module reference
  fly-by speed (100 m/s, mid range of a PEC sweep) unless the
  scheduled pass indicated airspeed is passed explicitly; the result
  carries the sign of the height error, a low altimeter reading gives
  a positive correction.
- Trailing cone method: the reference static pressure comes from a
  cone trailed behind the aircraft clear of the fuselage flow; the
  reduction to dVp follows the same static pressure error chain as the
  tower fly-by at the flown indicated airspeed.
- GPS ground speed doublet: two runs on reciprocal headings at the
  same indicated airspeed give ground speeds V1g and V2g; with a
  steady wind the true airspeed is V_tas = (V1g + V2g)/2, the
  calibrated airspeed is V_cas = V_tas * sqrt(rho/rho0) with the
  density ratio at the test altitude, and dVp = V_cas - V_ias.
- PEC curve: the calibrated points (V_ias, dVp) become the knots of a
  piecewise linear position error correction curve; repeat passes at a
  scheduled speed are combined by their least squares mean, and the
  residual RMS of the observations about the curve is the data quality
  metric.
- PEC table: for each indicated airspeed the table row carries dVp
  from the curve and V_cas = V_ias + dVp; the table feeds the data
  reduction of every later flight.
- Data quality verdict: coverage is the fraction of planned test point
  speeds that lie inside the calibrated span; the verdict is adequate
  when coverage is at least 0.95 and the residual RMS is at most
  1.0 m/s.
- Units are SI: speeds m/s, pressures Pa, heights m, temperatures K.
  FAR-25 and CS-25 set the airspeed instrument accuracy context for
  the certification flight test; the relations above are standard
  engineering methodology, summary-only per standards-map.yaml.

## Workflow

1. Schedule the PEC test points across the speed range with
   test-point-matrix-design: choose the reference methods (tower
   fly-by, trailing cone, GPS ground speed doublet), the indicated
   airspeeds per point, and repeat passes for the data quality check.
2. Convert the recorded impact pressure channel to calibrated
   airspeed with calibrated_airspeed, or convert a scheduled calibrated
   airspeed to its impact pressure with impact_pressure_from_cas for
   the test card.
3. Reduce a tower fly-by pass: call tower_flyby_position_error with
   the surveyed geometric height, the altimeter pressure altitude, and
   the measured temperature (and the pass indicated airspeed when it
   was recorded); the returned dVp belongs to that pass point.
4. Reduce a GPS ground speed doublet: gps_doublet_tas on the two
   reciprocal ground speeds, tas_to_cas with the density ratio of the
   test altitude, then position_error against the indicated airspeed
   held during the doublet.
5. Combine the calibrated points from every method into one set of
   (V_ias, dVp) observations and fit the correction curve with
   fit_pec_curve; inspect the residual RMS it reports.
6. Build the PEC table with pec_table over the scheduled indicated
   airspeeds; each row carries the correction and the calibrated
   airspeed that the data reduction will use.
7. Run pec_verdict with the planned point list and the methods flown
   to get the coverage, residual RMS, method list, and the adequate or
   review verdict.
8. Hand the PEC table to flight-test-data-reduction for the channel
   reduction of the campaign and to v-speeds for the speed rule
   assessment on calibrated values.
9. Confirm the deterministic checks with the contract test
   scripts/test_position_error_calibration.py.

## Worked example

- Compressible identity: impact_pressure_from_cas(100.0) returns
  6258.4 Pa and calibrated_airspeed of that pressure returns
  99.99999999999982 m/s, so position_error(100.0, V_cas) is zero by
  construction; V_cas equals V_ias whenever the position error is
  zero.
- Tower fly-by: the aircraft passes at geometric height 500 m and the
  altimeter reads 490 m (10 m low) at 288.15 K. The hydrostatic
  altimeter scale gives dp_s = rho * g0 * 10 m = 113.3 Pa, which
  displaces the impact pressure the airspeed indicator sees; at the
  reference pass speed of 100 m/s the reduction returns
  dVp = +0.88 m/s (the indicator reads low, the correction is added).
  The same pass with the altimeter 10 m high returns dVp = -0.89 m/s,
  and a zero height error returns 0.0. Passing the actual pass speed
  refines the scale: 90 m/s gives 0.99 m/s, 120 m/s gives 0.72 m/s.
- GPS ground speed doublet: reciprocal runs give V1g = 98 m/s and
  V2g = 102 m/s, so gps_doublet_tas returns V_tas = 100 m/s. At a
  density ratio rho/rho0 = 0.9 the calibrated airspeed is
  tas_to_cas(100.0, 0.9) = 94.87 m/s; held at V_ias = 100 m/s the
  point carries dVp = -5.13 m/s, the indicator reads high at this
  speed.
- PEC curve: five points (60, 1.2), (80, 0.9), (100, 0.6), (120, 0.2),
  (140, -0.3) fit to a curve whose knots reproduce every point with
  residual RMS 2.5e-17 (zero to float precision); the segment slopes
  are -0.015, -0.015, -0.02, -0.025 m/s per m/s. The table row at
  70 m/s interpolates dVp = 1.05 m/s and V_cas = 71.05 m/s.
- Verdict: seven planned points spanning 55 to 145 m/s with a
  calibrated span of 60 to 140 m/s give coverage 5/7 = 0.714, below
  the 0.95 threshold, so the verdict is review until the span covers
  the planned points.

## Verification

- Confirm calibrated_airspeed(impact_pressure_from_cas(100.0)) returns
  100 m/s and that the round trip holds at every test speed.
- Confirm gps_doublet_tas(98.0, 102.0) returns 100.0 and
  tas_to_cas(100.0, 0.9) returns 94.87 m/s.
- Confirm tower_flyby_position_error(500.0, 490.0, 288.15) returns
  about +0.88 m/s, that the sign follows the height error, and that a
  zero height error returns zero.
- Confirm fit_pec_curve reproduces its knots with residual RMS near
  zero and that repeat passes collapse to their mean with the scatter
  reported in the residual RMS.
- Confirm pec_table interpolates the curve and returns
  (v_ias, dVp, v_ias + dVp) rows for strictly increasing speeds.
- Confirm ValueError rejection of negative speeds, empty lists, a
  density ratio of zero or less, non-monotonic table speeds, negative
  geometric height, and a non-positive temperature.
- Run the contract test offline: python3
  scripts/test_position_error_calibration.py (34 tests, deterministic).

## Related leaves

- flight-test-operations/planning/flight-test-data-reduction: consumes
  the PEC table when it applies the calibration corrections and
  computes the corrected airspeed of each recorded run.
- flight-test-operations/envelope/v-speeds: consumes the calibrated
  airspeed set for the certified speed rules of the program.
- flight-test-operations/envelope/high-angle-of-attack-testing: runs
  the angle of attack sensor position error calibration against its
  own tower fly-by or trailing cone reference at high angles, the
  companion method to this leaf's airspeed PEC.
- flight-test-operations/planning/test-point-matrix-design: lays out
  the condition sweeps that schedule the PEC points across the speed
  range.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_position_error_calibration.py

The test covers the compressible calibrated airspeed identities and
the zero position error identity, the GPS ground speed doublet worked
example (98/102 m/s to 100 m/s true airspeed, 94.87 m/s calibrated at
a 0.9 density ratio), the tower fly-by height error reduction with its
sign, magnitude, pass speed sensitivity, and zero error behavior, the
piecewise linear PEC fit that reproduces its knots with near zero
residual RMS, repeat pass averaging, table interpolation, the coverage
and verdict math, and ValueError rejection of negative speeds, empty
lists, a non-positive density ratio, non-monotonic table speeds, a
negative geometric height, and a non-positive temperature.

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 airspeed
  instrument requirements frame the certification context by name; the
  airspeed relations and the PEC reduction above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
