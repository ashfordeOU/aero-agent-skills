# Wave-25 leaf spec: position-error-calibration (flight-test-operations)

- Path: skills/flight-test-operations/planning/position-error-calibration/
- Pack: planning (existing siblings: flight-test-planning,
  flight-test-data-reduction, flight-test-instrumentation,
  flight-test-safety, telemetry-data-acquisition,
  test-point-matrix-design)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-test-operations

## Claim

Plan and reduce the airspeed position error calibration (PEC) flight
test for a fixed-wing aircraft: compute the calibrated airspeed from the
indicated airspeed and the position error correction, plan the test
points for the tower fly-by, trailing cone, and GPS ground-speed
methods, reduce the tower fly-by run into the height error and the
position error, convert the GPS ground-speed doublet into the
calibrated airspeed at the test altitude, fit the position error
correction curve against the indicated airspeed, and produce the PEC
table with the corrected airspeeds that gate the flight test data
reduction. Produces the position error at each point, the fitted PEC
curve, the calibrated airspeed set, and the data quality verdict.

Does NOT do: generic channel calibration and time series reduction
(flight-test-data-reduction owns slope/intercept channel calibration,
smoothing, combined uncertainty), AoA sensor calibration (high-angle-
of-attack-testing owns the AoA position error against tower fly-by),
v-speeds computation from calibrated data (v-speeds leaf owns the Vref,
V2, Vr rules). This leaf owns the airspeed PEC flight test method itself.

## Model (implement exactly)

- Standard atmosphere airspeed relations (use module constants, ISA):
  q_c = p0 * ((1 + 0.2*(V_cas/a0)^2)^3.5 - 1) compressible dynamic
  pressure. Calibrated airspeed from impact pressure:
  V_cas = a0 * sqrt(5 * ((q_c/p0 + 1)^(2/7) - 1)) with a0 = 340.294 m/s
  and p0 = 101325 Pa (sea level standard) - implement the standard
  form and assert the identity V_cas == V_ias when position error 0.
- Position error: V_cas = V_ias + dVp(V_ias) where dVp is the position
  error correction; PEC curve fitted as a piecewise-linear function of
  V_ias over the calibrated test points.
- Tower fly-by reduction: the aircraft flies level at a known height
  above the tower; the tower observer records the fly-by height; the
  pressure altitude error is the difference between the geometric height
  (corrected for the height above the tower) and the pressure altitude
  from the altimeter; convert the altimeter error to the airspeed
  position error through the altimeter scale relation (state the
  simplified standard relation you use).
- GPS ground-speed method (doublet): two runs on reciprocal headings at
  the same indicated airspeed; true airspeed from the ground speeds
  V1g, V2g and the wind component: V_tas = (V1g + V2g)/2 when the wind is
  steady; then V_cas = V_tas * sqrt(rho/rho0) (density ratio); position
  error dVp = V_cas - V_ias.
- Fit: least squares piecewise linear PEC over the V_ias breakpoints;
  report the residual RMS as the data quality metric.
Functions:
- calibrated_airspeed(qc) -> V_cas
- impact_pressure_from_cas(v_cas) -> qc
- position_error(v_ias, v_cas) -> dVp
- tower_flyby_position_error(geometric_height, pressure_altitude,
  temperature) -> dVp
- gps_doublet_tas(v1g, v2g) -> V_tas
- tas_to_cas(v_tas, density_ratio) -> V_cas
- fit_pec_curve(points) -> (breakpoints, slopes, residual_rms)
- pec_table(v_ias_list, curve) -> list of (v_ias, dVp, v_cas)
- pec_verdict(...) -> dict (residual RMS, coverage, method list)
ValueError on: negative speeds, empty lists, density ratio <= 0,
non-monotonic v_ias inputs.

## Worked example

- Impact pressure identity: V_ias = V_cas = 100 m/s gives zero dVp by
  construction (assert).
- GPS doublet: V1g = 98 m/s, V2g = 102 m/s -> V_tas = 100 m/s, at
  rho/rho0 = 0.9, V_cas ~ 94.87 m/s (assert within tolerance), dVp vs
  V_ias given.
- Fit PEC on 5 synthetic points and assert the piecewise interpolation
  reproduces the points and residual RMS ~ 0.
- Tower fly-by reduction returns a finite dVp with the sign consistent
  with the height error.
Keep at least 18 test methods.

## Corpus tasks (ids w25-position-error-calibration-1/2)

Distinctive tokens: position error calibration, PEC, airspeed
calibration, calibrated airspeed, tower fly-by, trailing cone, GPS
ground speed doublet, position error correction curve. Avoid: angle of
attack sensor, channel slope intercept, smoothing, Vref, V2 (owned by
high-AOA/data-reduction/v-speeds).

1. "plan the airspeed position error calibration points and reduce the
   GPS ground speed doublet runs into the calibrated airspeed and the
   position error correction curve for the flight test"
2. "compute the position error from the tower fly-by height comparison
   and build the PEC table of indicated versus calibrated airspeed"

## SKILL body notes

Pair with flight-test-data-reduction (uses the PEC table), v-speeds
(consumes calibrated airspeeds), high-angle-of-attack-testing (AoA PEC
methods). Worked example uses module constants and real outputs.
Compliance: FAR/CS 25 airspeed instrument requirements referenced by
name, no reproduced text.
