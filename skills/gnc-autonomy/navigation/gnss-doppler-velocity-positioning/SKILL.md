---
name: gnss-doppler-velocity-positioning
description: "Use when you must estimate the 3-D velocity of a GNSS receiver and its receiver clock drift at a single epoch from carrier-phase delta-range-rate (doppler) observables: propagate each satellite ECEF position and velocity from the broadcast-ephemeris Kepler elements, form the line-of-sight unit vector from the receiver position (pseudorange fix first, or supplied), predict the range rate rho_dot = (v_sat - v_rec) dot u + c*dt_dot, and solve the iterated least-squares system over the per-satellite doppler residuals, rows [u, -1.0], by 4x4 normal equations for the receiver velocity and clock drift. Produces the velocity fix in m/s with the per-axis 1-sigma precision from the doppler covariance, the recovered clock drift in m/s and s/s, the post-fit residual RMS and the convergence state that gate the navigation velocity output. Trigger: receiver velocity fix, doppler positioning, carrier delta range rate, clock drift estimate, velocity fix per-axis precision."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-229
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [gnss-doppler-velocity-positioning, receiver-velocity-fix, doppler-positioning, clock-drift-estimate, carrier-delta-range-rate, velocity-fix-per-axis-precision]
  version: 0.1.0
  author: AeroSkills
---

# GNSS Doppler Velocity Positioning (gnc-autonomy/navigation/gnss-doppler-velocity-positioning)

Use when you must estimate the 3-D ECEF velocity of a GNSS receiver and its
receiver clock drift at a single epoch from per-satellite carrier-phase
delta-range-rate (doppler) observables. Each tracked satellite is
propagated from its broadcast-ephemeris Kepler elements to the
light-time-corrected transmit epoch; the range-rate model
rho_dot = (v_sat - v_rec) dot u + c*(dtr_dot - dts_dot) linearizes into
the geometry rows [u_x, u_y, u_z, -1.0] over the unknown state
(vx, vy, vz, c*dtr_dot), and the iterated least-squares normal equations
are solved by Gaussian elimination until the state correction falls below
tolerance. The receiver position enters from a pseudorange fix first or is
supplied; the internal pseudorange seed is never a reported output. The
module is pure stdlib math, deterministic, with no RNG anywhere. It pairs
with gnss-pseudorange-positioning for the position snapshot and with
gnss-carrier-smoothing for the smoothing side of the carrier observable;
both fences are described under Related leaves.

## Domain quick reference

- Module constants: MU_EARTH = 3.986004418e14 m^3/s^2, OMEGA_EARTH =
  7.2921150e-5 rad/s, C_LIGHT = 299792458.0 m/s, R_EARTH = 6378137.0 m
  (spherical-earth demo receiver context), THETA_G0 = 1.1 rad (GMST at the
  epoch, linear model theta(t) = THETA_G0 + OMEGA_EARTH*t),
  EPHEMERIS_WINDOW = 7200.0 s, NEWTON_TOL = 1e-14, NEWTON_MAX = 60.
- Observable: the carrier-phase delta-range-rate (doppler) observable in
  m/s is y_i = (v_sat_i - v_rec) dot u_i + c*(dtr_dot - dts_dot_i) +
  eps_i, with u_i the unit line of sight from the receiver to the
  satellite, v_rec the unknown receiver ECEF velocity and the receiver and
  broadcast clock drifts (s/s) both scaled by c inside the model.
- Geometry epoch: the satellite state that produced the received signal is
  evaluated at the transmit epoch t_tx = epoch - rho/c with rho the
  geometric range, found by iteration; the light-time correction moves each
  satellite about 300 m between reception and transmit evaluation. The LOS
  runs from the receiver position at the reception epoch to the satellite
  position at its transmit epoch.
- Linearized system: with the unknown state x = (vx, vy, vz, c*dtr_dot),
  the range-rate equation rearranges to u_i dot v_rec - c*dtr_dot =
  v_sat_i dot u_i - c*dts_dot_i - y_i, so geometry row i is
  [u_x, u_y, u_z, -1.0] and rhs_i = v_sat_i dot u_i - c*dts_dot_i - y_i.
  At least 4 satellites are needed; each pass solves the 4x4 normal
  equations (H^T H) x = H^T z.
- Iteration: every pass re-evaluates each satellite state at its transmit
  epoch, rebuilds the rows and rhs, and re-solves until the max state
  correction falls below tol (deterministic: converges in 4 passes at
  tol = 1e-9 on the worked example).
- Residual and precision: residual r_i = y_i - rho_dot_predicted with
  rho_dot_predicted = (v_sat - v_rec) dot u + c*(dtr_dot - dts_dot);
  residual_rms = sqrt(mean(r_i^2)); sigma0 = sqrt(sum(r_i^2)/(n - 4)) for
  n > 4 (else the supplied doppler_sigma, default 0.05 m/s). The per-axis
  1-sigma precision is sigma0*sqrt(diag_ii((H^T H)^-1)) on the three
  velocity axes and sigma0*sqrt(diag_44) for the clock drift term, the
  covariance diagonal taken from the converged normal matrix.
- Kepler propagation: two-body from the broadcast-style element record
  (a, e, inc, raan, argp, M0 at toe), mean motion n = sqrt(MU/a^3), the
  eccentric anomaly by Newton iteration on E - e sin E = M, perifocal
  position and velocity rotated to ECI by Rz(raan)*Rx(inc)*Rz(argp), and
  ECI-to-ECEF with v_ecef = R3(-theta) v_eci - omega_earth x r_ecef.
- Pseudorange seed: the internal geometry feeder solves the iterated
  position LS with rows [-u, 1.0] over (x, y, z, clock bias in m) from
  pseudorange records; it only supplies the receiver position when none is
  provided and is never reported as an output of this leaf.
- RTCA DO-229 frames the GNSS receiver navigation context; the relations
  above are standard engineering methodology, name and paraphrase only.

## Workflow

1. Fix the measurement set: the satellite element records, the carrier
   delta-range-rate doppler observables y_i (m/s) at the reception epoch
   and the receiver ECEF position (supplied position fix, or the internal
   seed of step 2). mean_to_eccentric and the module constants anchor every
   later step.
2. Seed the receiver position when none is supplied:
   pseudorange_position runs the iterated position least squares over the
   pseudorange records and returns the geometry seed position only; the
   position and clock bias are never reported outputs of this leaf.
3. Propagate every satellite to the light-time-corrected transmit epoch:
   kepler_state_eci propagates the two-body ECI state from the
   broadcast-ephemeris elements (mean anomaly advanced, Kepler equation
   solved, perifocal frame rotated to ECI) and ecef_state rotates it into
   ECEF with the linear GMST model and the omega x r term.
4. Form the line-of-sight geometry: line_of_sight returns the unit vector
   u from the receiver to the satellite and the geometric range rho that
   fixes the transmit-epoch offset rho/c.
5. Predict the range rate of a candidate state:
   predicted_range_rate applies rho_dot = (v_sat - v_rec) dot u +
   c*(dtr_dot - dts_dot), the claim-form observable.
6. Solve the 4x4 linear system: solve_normal4 runs Gaussian elimination
   with partial pivoting on the normal equations of each pass; the clock
   column carries the minus sign of the rearranged equation, so row dot
   state = u dot v_rec - c*dtr_dot by construction.
7. Run the iterated velocity fix: velocity_least_squares builds the rows
   [u, -1.0] and rhs v_sat dot u - c*dts_dot - y_i over the doppler
   residuals, re-evaluates the satellite states at the refreshed transmit
   epochs each pass, and returns the report dict with the velocity, the
   clock drift, the residuals and the precision terms.
8. Read off the navigation outputs: the velocity fix (m/s), the recovered
   clock drift in m/s and s/s, the post-fit residual RMS, sigma0 and the
   per-axis 1-sigma precision from the doppler covariance, plus the
   convergence state. These gate the navigation velocity output; confirm
   with the contract test of the Behavior contract (gate 3) section.

## Worked example

Demo receiver at the equator on the prime meridian, ECEF position
(6378137.000000, 0.000000, 0.000000) m (lat 0, lon 0, sea level on the
spherical earth), moving due north at 250 m/s, so the TRUE ECEF velocity
is (0.000000, 0.000000, 250.000000) m/s. TRUE receiver clock bias
1.200e-07 s and clock drift 1.200e-09 s/s (0.359751 m/s). Seven MEO
satellites at 55.5 deg inclination with semi-major axes near 2.656e7 m
placed so all seven sit above the local horizon (elevations 10.7 to
50.8 deg), toe = 0 s, reception epoch t = 0 s, THETA_G0 = 1.1 rad. All
values below are REAL outputs of the leaf module (stdlib math,
deterministic, exit 0), identical to the wave-43 spec anchors.

Constellation (broadcast-ephemeris style elements, deg; dts0 in s, dts_dot
in s/s, argp 0 for all):

- A: a 26560000.0 m, e 0.0080, raan -33.5573, M0 56.6777, dts0 -4.200e-09,
  dts_dot -1.700e-10
- B: a 26558000.0 m, e 0.0120, raan 44.6470, M0 36.5232, dts0 2.800e-09,
  dts_dot 9.000e-11
- C: a 26562000.0 m, e 0.0060, raan 104.6252, M0 14.4399, dts0 -1.900e-09,
  dts_dot 2.100e-10
- D: a 26559000.0 m, e 0.0150, raan 98.5683, M0 -9.4352, dts0 3.600e-09,
  dts_dot -6.000e-11
- E: a 26561000.0 m, e 0.0100, raan 141.4038, M0 -36.6604, dts0 -2.500e-09,
  dts_dot 1.300e-10
- F: a 26560000.0 m, e 0.0180, raan 91.2561, M0 -52.6231, dts0 1.400e-09,
  dts_dot -2.400e-10
- G: a 26557000.0 m, e 0.0090, raan 17.4134, M0 17.9818, dts0 -3.100e-09,
  dts_dot 5.000e-11

Simulated doppler observables y_i (carrier delta range rate, m/s), with
documented deterministic noise offsets (m/s): A -270.264366 (noise
-0.031), B 342.286009 (0.024), C 143.629913 (0.045), D -29.518775
(-0.019), E 84.049775 (0.012), F -417.444778 (-0.037), G 56.378270
(0.028).

Velocity fix, receiver position SUPPLIED (the true position):

- Recovered velocity (m/s) (-0.023031, -0.027232, 249.970234), so the
  per-axis error is (-0.023031, -0.027232, -0.029766) m/s and the 3-D
  error is 0.046455 m/s: the 250 m/s north motion is recovered within
  0.03 m/s on every axis.
- Recovered clock drift 0.345501 m/s = 1.152e-09 s/s versus the true
  0.359751 m/s, error -0.014250 m/s (the broadcast dts_dot terms are
  absorbed correctly, leaving the receiver drift as the 4th unknown).
- Residual RMS 0.023142 m/s, sigma0 0.035350 m/s (7 satellites, 3 degrees
  of freedom), iterations 4, converged True.
- Per-axis 1-sigma precision (0.061974, 0.024222, 0.026807) m/s; the
  radial (x, local vertical) axis is the weakest, as expected for a
  horizon-confined geometry; clock drift 1-sigma 0.035651 m/s.

Pseudorange position feeder arm (geometry seed only, position never a
deliverable): the feeder converges to position (6378135.178265,
-1.180589, -1.303811) m, 3-D error 2.532 m, lumped clock bias 35.266 m,
residual RMS 1.630 m, iterations 5. Feeding that position into the doppler
LS recovers velocity (-0.023155, -0.027322, 249.970080) m/s, 3-D error
0.046667 m/s, and the maximum per-axis velocity difference versus the
supplied-position run is 1.537e-04 m/s, so the velocity fix is insensitive
to the position-seed error at the sub-mm/s level.

Noiseless cross-check: with the noise offsets set to zero, the LS recovers
(0.000000, 0.000000, 250.000000) m/s with 3-D error 1.649e-13 m/s and
residual RMS 1.075e-13 m/s (float noise only, still 4 iterations): the
exact-recovery identity of the linearized system.

Read-off: carrier-phase delta-range-rate observables from a 7-satellite
geometry with about 0.03 m/s measurement noise give a snapshot velocity
fix accurate to about 0.03-0.05 m/s per axis (about 0.1 percent of the
250 m/s platform speed) with the receiver clock drift recovered to
0.014 m/s, and the vertical (radial) axis carries the largest 1-sigma
precision of about 0.062 m/s.

## Verification

- Run scripts/test_gnss_doppler_velocity_positioning.py; the contract test
  must pass under both the system python3 and the pyenv 3.13.12 hook
  interpreter (46 tests, offline, deterministic).
- Confirm the worked-example contract: per-axis velocity error below
  0.10 m/s on every axis and 3-D error below 0.15 m/s (anchor 0.046455),
  recovered clock drift within 0.05 m/s of 0.359751 m/s (anchor error
  -0.014250), residual RMS below 0.05 m/s (anchor 0.023142), at most 8
  iterations and converged True.
- Confirm the precision read-off: per_axis_sigma_mps equals sigma0 times
  the square root of the covariance diagonal, the anchor per-axis values
  (0.061974, 0.024222, 0.026807) m/s hold within 1e-3 and the clock drift
  sigma 0.035651 m/s within 1e-3.
- Confirm clock_drift_mps = C_LIGHT * clock_drift_sps (the same float
  divided by C_LIGHT, exact).
- Confirm the noiseless identity: zero noise offsets recover the true
  velocity with 3-D error below 1e-6 m/s per axis (anchor 1.649e-13) and
  residual RMS below 1e-6 m/s.
- Confirm the feeder arm: pseudorange_position on the documented
  pseudoranges returns a position within 5 m of the truth (anchor 3-D
  error 2.532 m) and the resulting velocity fix differs from the
  supplied-position run by less than 1e-3 m/s per axis (anchor 1.537e-04).
- Confirm the Kepler sanity band: each satellite ECEF speed lies between
  2500 and 3500 m/s (anchor 2926-3245), each elevation lies above 5 deg
  and the light-time correction stays below 0.1 s.
- Confirm ValueError rejection of every non-physical input: e = 1.0 and
  e < 0 in mean_to_eccentric and kepler_state_eci, a <= 0, epochs outside
  the 7200 s ephemeris window, missing or non-finite element keys, a
  satellite coincident with the receiver, fewer than 4 satellites, doppler
  or pseudorange length mismatch, non-finite receiver position, doppler,
  epoch or clock seed, iters = 0 and a singular 4x4 system.
- Confirm the module imports nothing beyond math and contains no RNG.

## Related leaves

- skills/gnc-autonomy/navigation/gnss-pseudorange-positioning: the
  position-domain sibling that owns the snapshot position and clock-bias
  solution from pseudoranges; here the pseudorange solve is only the
  internal geometry seed and the position is never a reported output.
- skills/gnc-autonomy/navigation/gnss-carrier-smoothing: owns the Hatch
  smoothing side of the carrier observable; this leaf consumes only the
  delta-range-rate observable and runs no smoothing recursion.
- skills/gnc-autonomy/navigation/gnss-raim-fde: owns integrity on the
  pseudorange set; this leaf treats the doppler set as fault-free.
- skills/gnc-autonomy/navigation/gnss-carrier-smoothing and
  skills/gnc-autonomy/navigation/dilution-of-precision: the remaining
  GNSS navigation siblings of the pack.
- skills/gnc-autonomy/space/orbit-determination and
  skills/gnc-autonomy/space/orbit-dynamics: the space-domain siblings;
  the two-body Kepler propagation of broadcast-style elements to ECEF
  satellite velocities is new to gnc-autonomy here.
- skills/space-systems/subsystems/doppler-shift: the spacecraft-comm
  frequency-domain sibling; this leaf works in the range-rate domain in
  m/s only and never computes a received frequency or offset.

## Pitfalls

- Confusing this leaf with the position snapshot: the doppler LS solves
  only the receiver velocity and clock drift. The position fix and clock
  bias of the snapshot belong to gnss-pseudorange-positioning; here the
  pseudorange solve is an internal geometry seed and the position is never
  a reported output.
- Treating the observable as raw carrier phase: this leaf consumes the
  carrier-phase delta-range-rate (doppler) observable in m/s only. Hatch
  smoothing, smoothed range recursion, code-carrier divergence monitoring
  and raw carrier-phase accumulation belong to gnss-carrier-smoothing.
- Working in the frequency domain: satellite velocities are never turned
  into received frequencies, delta-f offsets or acquisition frequencies;
  that is the spacecraft-comm domain of space-systems/subsystems/
  doppler-shift. This leaf stays in m/s throughout.
- Ignoring the light-time correction: evaluating every satellite at the
  reception epoch instead of the transmit epoch t_tx = epoch - rho/c moves
  each state about 300 m, a real effect at the cm/s level of the velocity
  fix; the iteration in velocity_least_squares handles it.
- Forgetting the clock drift is the 4th unknown: the state is
  (vx, vy, vz, c*dtr_dot) with geometry rows [u, -1.0]; solving a 3-axis
  velocity-only system over the doppler residuals absorbs the receiver
  clock drift into every axis and corrupts the fix.
- Reading sigma0 with only 4 satellites: with n = 4 there are zero residual
  degrees of freedom, so sigma0 falls back to the supplied doppler_sigma
  (default 0.05 m/s); the covariance diagonal still reflects the geometry.
- Quoting the vertical axis precision as if it matched the horizontal: the
  radial (local vertical) axis is the weakest for a horizon-confined
  constellation (anchor 1-sigma 0.061974 m/s versus 0.024-0.027 m/s on the
  other axes).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/gnc-autonomy/navigation/gnss-doppler-velocity-\
positioning/scripts/test_gnss_doppler_velocity_positioning.py

The test covers the worked-example contract with the module's real outputs
as targets: the step-1 module constants and measurement context, the
step-2 pseudorange_position geometry seed with its position and velocity
insensitivity bounds, the step-3 Kepler propagation and ECEF rotation
identities (circular-orbit sanity, period round trip, earth-rotation
subtraction), the step-4 line-of-sight geometry, the step-5
predicted_range_rate formula with the c-scaled net drift, the step-6
solve_normal4 solve and the row identity that pins the minus sign of the
clock column, the step-7 velocity_least_squares iterated fix on the worked
example (velocity, clock drift, residual RMS, sigma0, convergence) and the
step-8 precision read-off (per-axis sigma identity and anchor values), the
noiseless exact-recovery identity, the constellation sanity band (ECEF
speeds, elevations, light-time scale), ValueError rejection of every
non-physical input in the spec validation list, determinism across reruns
and the pure-stdlib no-RNG import check. It passes under both the system
python3 and the pyenv 3.13.12 hook interpreter.

## Compliance

- Standards referenced, not reproduced: RTCA DO-229 frames the GNSS
  receiver navigation context; this leaf implements standard engineering
  methodology with name and paraphrase only, no MOPS algorithm or table
  text, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
