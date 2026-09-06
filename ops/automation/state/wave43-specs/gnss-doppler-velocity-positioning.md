# Wave-43 leaf spec: gnss-doppler-velocity-positioning (gnc-autonomy,
# navigation pack)

- Path: skills/gnc-autonomy/navigation/gnss-doppler-velocity-positioning/
- Pack: navigation (present siblings bearing-only-localization,
  dilution-of-precision, gnss-carrier-smoothing, gnss-pseudorange-
  positioning, gnss-raim-fde, inertial-navigation, ins-gnss-integrated-
  filter, kalman-filter-design, navigation-frames; adjacent fences in
  gnc-autonomy/space/orbit-determination and gnc-autonomy/space/
  orbit-dynamics).
- Provenance: wave-43 probe receipt #1 (GNC 45, leaf-plan line 33):
  snapshot receiver velocity + clock-drift fix from carrier
  delta-range-rate (doppler) observables by iterated least squares, the
  position-domain sibling gnss-pseudorange-positioning owning only the
  position + clock-bias snapshot; whole-tree grep at prep found ZERO
  doppler or range-rate content in gnc-autonomy and no receiver-velocity
  leaf anywhere in the tree (verified below).
- Claim fences (quoted from the sibling frontmatter at prep, none owns the
  snapshot velocity fix from doppler observables):
  - gnss-pseudorange-positioning (this pack, position-domain sibling)
    solves the position snapshot only: its description reads "compute a
    GNSS receiver position fix from pseudorange measurements: given
    satellite positions in ECEF and their pseudoranges (geometric range
    plus receiver clock bias), solve the four-unknown navigation
    equations for x, y, z and clock bias" and its body states "The leaf
    is a snapshot solution: no smoothing, no dynamics model". It does
    NOT estimate velocity; nothing in its quick reference or workflow
    mentions a velocity, a range rate or a clock drift.
  - gnss-carrier-smoothing (this pack) OWNS the smoothing side of the
    carrier: its description reads "smooth GNSS code pseudoranges with
    carrier-phase delta ranges before positioning: run the first-order
    Hatch recursion at a smoothing time constant ... and monitor the
    code-carrier ionospheric divergence". The new leaf only consumes the
    doppler/range-rate observable (carrier-phase delta-range-rate scaled
    to m/s) as a measurement; it does NOT run Hatch smoothing, does NOT
    carry smoothed ranges between epochs, does NOT monitor code-carrier
    divergence, and does NOT use raw carrier phase accumulation.
  - gnss-raim-fde (this pack) OWNS integrity on the pseudorange set: its
    description reads "run receiver autonomous integrity monitoring
    (RAIM) fault detection and exclusion on an overdetermined GNSS
    pseudorange measurement set ... chi-square threshold ... horizontal
    protection level". The new leaf produces no detection verdict, no
    protection level and no exclusion; it treats the doppler set as
    fault-free.
  - space-systems/subsystems/doppler-shift (space-systems) OWNS the
    spacecraft-comm doppler frequency domain: its description reads
    "compute the doppler frequency shift on a spacecraft link: derive
    the line-of-sight range rate from the circular-orbit altitude and
    the ground elevation angle, convert it to the received frequency and
    offset on an s-band downlink carrier" (straight-line overflight
    model, frequency-domain outputs for receiver acquisition). The new
    leaf works in the range-rate domain only (m/s), from carrier-phase
    delta-range-rate observables of a GNSS constellation propagated by
    Kepler elements; it never computes a received frequency, a delta-f
    offset, an acquisition frequency or a pass geometry, and its clock
    drift is the receiver clock drift, not a link frequency offset.
  - gnc-autonomy/space/orbit-determination (Gibbs and Herrick-Gibbs
    initial orbit determination from three inertial position vectors)
    and orbit-dynamics never propagate broadcast-ephemeris elements to
    ECEF satellite velocities; the two-body Kepler propagation from
    broadcast-style element records is new to gnc-autonomy.
  Whole-tree greps at prep: "doppler|range-rate|receiver velocity|clock
  drift" = 0 hits in skills/gnc-autonomy (all SKILL.md files) and 2 hits
  in the whole skills tree, both space-systems/doppler-shift (its
  family SKILL.md and its own); "receiver velocity|velocity fix|doppler
  positioning" = 0 hits everywhere. GENUINE gnc-autonomy gap (fresh
  probe, GO 2): no leaf estimates the receiver velocity and clock drift
  from GNSS doppler observables.
- Standards id: rtca-do-229 (reference-only, present in standards-map.yaml
  at line 303, gated: true, RTCA MOPS proprietary; name + paraphrase only,
  no MOPS algorithm or table text). Ledger Standard: rtca-do-229.
- Family: gnc-autonomy

## Claim

Estimate the 3-D ECEF velocity of a GNSS receiver and its receiver clock
drift at a single epoch from carrier-phase delta-range-rate (doppler)
observables. For each tracked satellite, propagate the satellite ECEF
position and velocity from the broadcast-ephemeris Kepler elements at the
light-time-corrected transmit epoch, compute the line-of-sight unit vector
u from the receiver position (obtained from a pseudorange solution first,
or supplied) to the satellite, and predict the range rate rho_dot =
(v_sat - v_rec) dot u + c*dt_dot from the satellite velocity, the receiver
velocity and the net clock drift. Form the iterated least-squares system
over the per-satellite doppler residuals with geometry rows [u_x, u_y,
u_z, -1.0] and the 4x4 normal equations solved by Gaussian elimination for
the 3-D receiver velocity and the receiver clock drift c*dt_dot, iterating
the satellite-state evaluation to the transmit epoch until the state
correction falls below tolerance. Report the velocity fix with the
per-axis 1-sigma precision from the doppler covariance (residual-based
sigma0 times the square root of the diagonal of the inverse normal
matrix), the recovered clock drift in m/s and s/s, the post-fit residual
RMS and the convergence state that gate the navigation velocity output.
Deterministic offline: doppler equations, iterated LS with the position
from a pseudorange solution first or supplied, satellite ECEF velocity
from broadcast-ephemeris Kepler propagation (two-body, Newton-iterated
eccentric anomaly, linear GMST ECI-to-ECEF rotation with the earth
rotation rate subtracted). Does NOT do: the position fix or clock-bias
positioning solution (gnss-pseudorange-positioning, the position-domain
sibling; here the pseudorange solve is only an internal geometry seed and
the position is never a reported output); carrier smoothing, Hatch
recursion, code-carrier divergence or raw carrier-phase accumulation
(gnss-carrier-smoothing; this leaf consumes only the delta-range-rate
observable); RAIM fault detection, protection levels or satellite
exclusion (gnss-raim-fde); spacecraft-comm doppler frequency shift and
received-frequency offset (space-systems/subsystems/doppler-shift); orbit
determination from tracking data (orbit-determination); J2 and higher
perturbations, ionospheric/tropospheric range-rate terms, earth-rotation
Sagnac terms beyond the ECEF frame rotation, cycle slips and integer
ambiguities. The receiver displacement during the signal transit
(about 19 m at 250 m/s over the roughly 0.08 s light time) is second
order and neglected by the deterministic model.

## Model (implement exactly)

Pure stdlib, math only, deterministic (no RNG anywhere, not even seeded).
Module constants: MU_EARTH = 3.986004418e14 m^3/s^2, OMEGA_EARTH =
7.2921150e-5 rad/s, C_LIGHT = 299792458.0 m/s, R_EARTH = 6378137.0 m
(spherical-Earth context for the demo receiver only), THETA_G0 = 1.1 rad
(GMST at the epoch, linear model theta(t) = THETA_G0 + OMEGA_EARTH*t),
EPHEMERIS_WINDOW = 7200.0 s (broadcast ephemeris validity), NEWTON_TOL =
1e-14, NEWTON_MAX = 60. Two private rotation helpers (Rz/Rx composition,
matrix-vector multiply) are internal; the module exposes 8 functions.

Defining relations (pin these exactly; every function below derives from
them):
- Observable: the carrier-phase delta-range-rate (doppler) observable in
  m/s is y_i = (v_sat_i - v_rec) dot u_i + c*(dtr_dot - dts_dot_i) +
  eps_i, with u_i the unit line of sight from the receiver to the
  satellite, v_rec the unknown receiver ECEF velocity, dtr_dot the
  unknown receiver clock drift (s/s) and dts_dot_i the broadcast
  satellite clock drift (s/s), both scaled by c inside the model.
- Geometry epoch: the satellite state that produced the received signal
  is evaluated at the transmit epoch t_tx = epoch - rho/c with rho the
  geometric range, so t_tx is found by iteration (the light-time
  correction moves each satellite about 300 m between reception and
  transmit evaluation, a real effect at the cm/s level of the velocity
  fix). The LOS is evaluated from the receiver position at the reception
  epoch to the satellite position at its transmit epoch.
- Linearized system: with the unknown state x = (vx, vy, vz, c*dtr_dot),
  the range-rate equation rearranges to u_i dot v_rec - c*dtr_dot =
  v_sat_i dot u_i - c*dts_dot_i - y_i, so geometry row i is
  [u_x, u_y, u_z, -1.0] and rhs_i = v_sat_i dot u_i - c*dts_dot_i -
  y_i. The 4 unknowns need at least 4 satellites; the normal equations
  (H^T H) x = H^T z are a 4x4 solve per pass.
- Iteration: each pass re-evaluates every satellite state at its
  transmit epoch, rebuilds the rows and rhs, and re-solves until the
  max state correction falls below tol (deterministic: converges in 4
  passes at tol = 1e-9 on the worked example).
- Residual and precision: residual r_i = y_i - rho_dot_predicted with
  rho_dot_predicted = (v_sat - v_rec) dot u + c*(dtr_dot - dts_dot);
  residual_rms = sqrt(mean(r_i^2)); sigma0 = sqrt(sum(r_i^2)/(n - 4))
  for n > 4 (else the supplied doppler_sigma, default 0.05 m/s); the
  per-axis 1-sigma precision is sigma0*sqrt(diag_ii((H^T H)^-1)) for the
  three velocity axes and sigma0*sqrt(diag_44) for the clock drift,
  with the covariance diagonal from the converged normal matrix.
- Kepler propagation: two-body from the broadcast-style element record
  (a, e, inc, raan, argp, M0 at toe), mean motion n = sqrt(MU/a^3), the
  eccentric anomaly by Newton iteration on E - e sin E = M, true
  anomaly, perifocal position and velocity, rotation to ECI by
  Rz(raan)*Rx(inc)*Rz(argp), and ECI-to-ECEF with v_ecef = R3(-theta)
  v_eci - omega_earth x r_ecef.
- Pseudorange seed: the internal geometry feeder solves the iterated
  position LS with rows [-u, 1.0] over (x, y, z, clock bias in m) from
  pseudorange records; used only to supply the receiver position when no
  position is provided, and never reported as an output of this leaf.

Functions:
- mean_to_eccentric(M, e) -> float. Newton iteration on
  E - e*sin(E) = M from E = M + e*sin(M). ValueError if M or e
  non-finite, or e outside [0, 1); ValueError if not converged in
  NEWTON_MAX steps.
- kepler_state_eci(sat, t) -> (pos, vel) tuple of ECI 3-vectors (m,
  m/s). Two-body propagation from the element record (keys id, a, e,
  inc, raan, argp, m0, toe, dts0, dts_dot). ValueErrors: missing keys;
  non-finite element or epoch; a <= 0; e outside [0, 1); |t - toe| >
  EPHEMERIS_WINDOW.
- ecef_state(r_eci, v_eci, t) -> (pos, vel) tuple in ECEF with the
  linear GMST model and v_ecef = R3(-theta) v_eci - omega x r_ecef.
  ValueError if the state is not two finite 3-vectors.
- line_of_sight(sat_pos, rec_pos) -> (u, rho) unit LOS receiver to
  satellite and range. ValueError if the range is below 1 m
  (satellite coincident with the receiver).
- predicted_range_rate(sat_vel, rec_vel, u, dts_dot, dtr_dot) -> float
  (v_sat - v_rec) dot u + C_LIGHT*(dtr_dot - dts_dot), the claim form
  rho_dot = (v_sat - v_rec) dot u + c*dt_dot with dt_dot the net
  receiver-minus-satellite drift. ValueError on non-finite input.
- solve_normal4(rows, rhs) -> 4-tuple. Gaussian elimination with partial
  pivoting on the 4x4 normal system. ValueError on non-finite input or a
  singular matrix (pivot below 1e-300).
- velocity_least_squares(satellites, doppler, receiver_position,
  epoch = 0.0, dtr_dot_seed = 0.0, iters = 8, tol = 1e-9,
  doppler_sigma = 0.05) -> dict. The iterated LS velocity fix described
  above; receiver_position is the supplied position fix (or the
  pseudorange-seed output); dtr_dot_seed starts the clock-drift state.
  Returns velocity (3-tuple m/s), clock_drift_mps, clock_drift_sps,
  residuals, residual_rms, sigma0, per_axis_sigma_mps, clock_drift_
  sigma_mps, covariance_diag, iterations, converged, num_satellites.
  ValueErrors: fewer than 4 satellites; doppler list length mismatch;
  non-finite receiver position, epoch, seed or doppler; iters < 1;
  tol <= 0; a bad satellite record; a singular normal matrix or a
  coincident satellite (propagated from the helpers).
- pseudorange_position(sat_positions, pseudoranges, iters = 8,
  tol = 1e-6) -> dict. Iterated position LS geometry seed (position,
  clock_bias_m, residual_rms, iterations, converged). ValueErrors:
  fewer than 4 satellites; length mismatch; non-finite positions or
  pseudoranges; singular geometry or coincident satellite.

Identities to test (closed form or tolerance-bounded):
- Noiseless recovery: with zero doppler noise the LS recovers the true
  velocity to float noise (real anchor 3-D error 1.649e-13 m/s,
  residual RMS 1.075e-13 m/s, still 4 iterations).
- Row identity: with row [u, -1.0] and state (vx, vy, vz, c*dtr_dot),
  row dot x = u dot v_rec - c*dtr_dot by construction, so the clock
  column carries the minus sign of the rearranged equation.
- Clock drift scaling: clock_drift_mps = C_LIGHT * clock_drift_sps
  exactly (same float divided by C_LIGHT).
- Precision identity: per_axis_sigma_mps = sigma0 *
  sqrt(covariance_diag axis) on the three axes and for the clock term;
  covariance_diag is the diagonal of the converged (H^T H)^-1.
- Geometry insensitivity: the velocity fix fed with the pseudorange-seed
  position (about 2.5 m off) differs from the supplied-truth-position
  run by at most 1.537e-4 m/s per axis (real anchor).
- Earth rotation: the ECEF satellite speed lies below the ECI circular
  speed by the projected omega x r term (real anchor |vel| 2926-3245
  m/s for the demo MEO constellation, all below the about 3874 m/s
  two-body speed).
- Determinism; no imports beyond math; no RNG; gamma-free two-body
  dynamics.

## Worked example

Demo receiver at the equator on the prime meridian, ECEF position
(6378137.000000, 0.000000, 0.000000) m (lat 0, lon 0, sea level on the
spherical earth), moving due north at 250 m/s, so the TRUE ECEF velocity
is (0.000000, 0.000000, 250.000000) m/s. TRUE receiver clock bias
1.200e-07 s and clock drift 1.200e-09 s/s (0.359751 m/s). Seven MEO
satellites at 55.5 deg inclination with semi-major axes near 2.656e7 m
placed so all seven sit above the local horizon (elevations 10.7 to
50.8 deg), toe = 0 s, reception epoch t = 0 s, THETA_G0 = 1.1 rad. All
values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_dopp.py (stdlib math, deterministic, exit 0, run
under /usr/bin/python3).

Constellation (broadcast-ephemeris style elements; RAAN, argp, M0 solved
in the anchor from the target ECEF subpoints, dts0 in s, dts_dot in s/s):

- A: a 26560000.0 m, e 0.0080, inc 55.5000 deg, raan -33.5573 deg,
  M0 56.6777 deg, dts0 -4.200e-09, dts_dot -1.700e-10.
- B: a 26558000.0 m, e 0.0120, raan 44.6470 deg, M0 36.5232 deg,
  dts0 2.800e-09, dts_dot 9.000e-11.
- C: a 26562000.0 m, e 0.0060, raan 104.6252 deg, M0 14.4399 deg,
  dts0 -1.900e-09, dts_dot 2.100e-10.
- D: a 26559000.0 m, e 0.0150, raan 98.5683 deg, M0 -9.4352 deg,
  dts0 3.600e-09, dts_dot -6.000e-11.
- E: a 26561000.0 m, e 0.0100, raan 141.4038 deg, M0 -36.6604 deg,
  dts0 -2.500e-09, dts_dot 1.300e-10.
- F: a 26560000.0 m, e 0.0180, raan 91.2561 deg, M0 -52.6231 deg,
  dts0 1.400e-09, dts_dot -2.400e-10.
- G: a 26557000.0 m, e 0.0090, raan 17.4134 deg, M0 17.9818 deg,
  dts0 -3.100e-09, dts_dot 5.000e-11.

All with argp 0.0000 deg and toe 0 s. Propagated ECEF states at the
light-time-corrected transmit epoch (position in km, speed in m/s,
range in km, elevation in deg):

- A: pos (10910.857, -15582.557, 18369.729) km, speed 2926.3687 m/s,
  range 24511.397 km, elevation 10.657 deg.
- B: pos (22692.721, 1985.293, 13151.452) km, speed 3091.9326 m/s,
  range 21049.174 km, elevation 50.811 deg.
- C: pos (16603.676, 19787.446, 5490.236) km, speed 3198.4424 m/s,
  range 22940.082 km, elevation 26.471 deg.
- D: pos (22440.022, 12955.724, -3641.850) km, speed 3245.0781 m/s,
  range 20954.665 km, elevation 50.041 deg.
- E: pos (13088.322, 18691.937, -13174.649) km, speed 3085.1449 m/s,
  range 23832.467 km, elevation 16.353 deg.
- F: pos (19229.566, -3390.808, -17581.751) km, speed 2976.9175 m/s,
  range 22040.299 km, elevation 35.668 deg.
- G: pos (20833.279, -14587.657, 6814.451) km, speed 3195.1503 m/s,
  range 21637.643 km, elevation 41.917 deg.

Simulated doppler observables y_i (carrier delta range rate, m/s) =
geometric (v_sat - v_rec) dot u + c*(dtr_dot_true - dts_dot) + noise,
with the documented deterministic noise offsets (m/s):

- A: geo -270.644082, clock term 0.410716, noise -0.031,
  y = -270.264366.
- B: geo 341.929239, clock term 0.332770, noise 0.024,
  y = 342.286009.
- C: geo 143.288118, clock term 0.296795, noise 0.045,
  y = 143.629913.
- D: geo -29.877514, clock term 0.377738, noise -0.019,
  y = -29.518775.
- E: geo 83.716997, clock term 0.320778, noise 0.012,
  y = 84.049775.
- F: geo -417.839479, clock term 0.431701, noise -0.037,
  y = -417.444778.
- G: geo 56.005508, clock term 0.344761, noise 0.028,
  y = 56.378270.

Velocity fix, receiver position SUPPLIED (the true position):
- Recovered velocity (m/s) (-0.023031, -0.027232, 249.970234), so the
  per-axis error is (-0.023031, -0.027232, -0.029766) m/s and the 3-D
  error is 0.046455 m/s: the 250 m/s north motion is recovered within
  0.03 m/s on every axis.
- Recovered clock drift 0.345501 m/s = 1.152e-09 s/s versus the true
  0.359751 m/s, error -0.014250 m/s (the broadcast dts_dot terms are
  absorbed correctly, leaving the receiver drift as the 4th unknown).
- Residual RMS 0.023142 m/s, sigma0 0.035350 m/s (7 satellites, 3
  degrees of freedom), iterations 4, converged True.
- Per-axis 1-sigma precision (0.061974, 0.024222, 0.026807) m/s; the
  radial (x, local vertical) axis is the weakest, as expected for a
  horizon-confined geometry; clock drift 1-sigma 0.035651 m/s.

Pseudorange position feeder arm (geometry seed only, position never a
deliverable): pseudoranges built from the same geometry with the receiver
bias 1.200e-07 s, per-satellite dts0 up to about 4.2 ns and documented
noise offsets about 1-3 m. The feeder converges to position
(6378135.178265, -1.180589, -1.303811) m, per-axis error
(-1.821735, -1.180589, -1.303811) m, 3-D error 2.532 m, lumped clock
bias 35.266 m, residual RMS 1.630 m, iterations 5. Feeding that position
into the doppler LS recovers velocity (-0.023155, -0.027322,
249.970080) m/s, 3-D error 0.046667 m/s, and the maximum per-axis
velocity difference versus the supplied-position run is 1.537e-04 m/s,
so the velocity fix is insensitive to the position-seed error at the
sub-mm/s level.

Noiseless cross-check: with the noise offsets set to zero, the LS
recovers (0.000000, 0.000000, 250.000000) m/s with 3-D error 1.649e-13
m/s and residual RMS 1.075e-13 m/s (float noise only, still 4
iterations): the exact-recovery identity of the linearized system.

Read-off: carrier-phase delta-range-rate observables from a 7-satellite
geometry with about 0.03 m/s measurement noise give a snapshot velocity
fix accurate to about 0.03-0.05 m/s per axis (about 0.1 percent of the
250 m/s platform speed) with the receiver clock drift recovered to
0.014 m/s, and the vertical (radial) axis carries the largest 1-sigma
precision of about 0.062 m/s.

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w43spec/anchor_dopp.py (stdlib math,
deterministic, exit 0).

## Validation list (contract test must include)

- Constellation and truth: the seven element records above, receiver
  position (6378137.0, 0.0, 0.0) m, true velocity (0.0, 0.0, 250.0)
  m/s, dtr_dot 1.2e-9 s/s, and the doppler measurements column y above
  (copy the printed values as inputs; no RNG needed in the test).
- velocity_least_squares on the worked set with the supplied true
  position: per-axis error below 0.10 m/s on every axis (anchor
  -0.023031, -0.027232, -0.029766), 3-D error below 0.15 m/s (anchor
  0.046455), clock drift within 0.05 m/s of 0.359751 m/s (anchor error
  -0.014250), residual RMS below 0.05 m/s (anchor 0.023142), iterations
  at most 8 and converged True.
- Per-axis precision: per_axis_sigma_mps equals sigma0 times the square
  root of the covariance diagonal, and the anchor values
  (0.061974, 0.024222, 0.026807) m/s hold within 1e-3; clock drift
  sigma 0.035651 m/s within 1e-3; clock_drift_mps = C_LIGHT *
  clock_drift_sps.
- Noiseless identity: with zero noise offsets the recovered velocity
  error is below 1e-6 m/s per axis (anchor 3-D error 1.649e-13 m/s) and
  residual RMS below 1e-6 m/s.
- Feeder arm: pseudorange_position on the documented pseudoranges returns
  a position within 5 m of the truth (anchor 3-D error 2.532 m) and the
  resulting velocity fix differs from the supplied-position run by less
  than 1e-3 m/s per axis (anchor 1.537e-04).
- Kepler sanity: each satellite ECEF speed lies between 2500 and 3500
  m/s (anchor 2926-3245), each elevation lies above 5 deg, and the
  light-time correction |t_tx| stays below 0.1 s.
- ValueErrors across the module: e = 1.0 and e < 0 in
  mean_to_eccentric and kepler_state_eci; a <= 0; t outside the 7200 s
  ephemeris window; missing or non-finite element keys; a satellite
  coincident with the receiver in line_of_sight (range below 1 m);
  fewer than 4 satellites in velocity_least_squares and
  pseudorange_position; doppler/pseudorange length mismatch; non-finite
  receiver position, doppler, epoch or seed; iters = 0; a singular 4x4
  system in solve_normal4.
- Determinism; no imports beyond math; no RNG anywhere in the module.

## Corpus fragment (eval/hit1-wave43-gnss-doppler-velocity-positioning.yaml)

Query 1 (copy verbatim):
  "estimate the 3-D receiver velocity vector and the receiver clock
  drift of a GNSS receiver from per-satellite carrier doppler
  range-rate measurements at a single epoch"
  intent: "gnc-autonomy; snapshot receiver velocity and clock drift fix
  from carrier delta-range-rate doppler observables by iterated least
  squares with per-axis precision"
  expected_skill: "gnc-autonomy/navigation/
  gnss-doppler-velocity-positioning"
Query 2 (copy verbatim):
  "recover the receiver velocity of a moving GNSS user from doppler
  observables given the satellite ECEF velocities propagated from the
  broadcast ephemeris"
  intent: "gnc-autonomy; doppler-based velocity positioning using
  Kepler-propagated satellite ECEF velocities and the line-of-sight
  range-rate residual system"
  expected_skill: "gnc-autonomy/navigation/
  gnss-doppler-velocity-positioning"
Task ids: w43-gnss-doppler-velocity-positioning-1 and -2. Prep grep of
eval/hit1-corpus.yaml: "gnss-doppler-velocity-positioning",
"receiver-velocity-fix", "doppler-positioning", "clock-drift-estimate",
"carrier-delta-range-rate", "velocity-fix-per-axis-precision" and
"range-rate-residual" all return ZERO hits; "receiver velocity",
"velocity fix" and "velocity positioning" appear in NO existing task.
All 7 "doppler" occurrences in the corpus belong to the two
w38-doppler-shift tasks (space-systems/subsystems/doppler-shift,
s-band downlink received-frequency and acquisition-offset domain, ids
w38-doppler-shift-1/-2) and the wave-38 comment line, none to a
navigation velocity task, so the queries above are collision-free. The
gnss-carrier-smoothing tasks route on Hatch smoothing and divergence
monitors, gnss-pseudorange-positioning tasks route on the position fix
and clock bias, and gnss-raim-fde tasks route on integrity thresholds
and protection levels, none of which these queries touch.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the 3-D velocity of a
GNSS receiver and its receiver clock drift at a single epoch from
carrier-phase delta-range-rate (doppler) observables:" and include the
velocity fix, the clock drift and the per-axis precision from the Claim.
First tag: gnss-doppler-velocity-positioning. Additional tags ONLY:
receiver-velocity-fix, doppler-positioning, clock-drift-estimate,
carrier-delta-range-rate, velocity-fix-per-axis-precision. NEVER single
generic words (gnss, doppler, velocity, positioning, clock, drift,
satellite, receiver, navigation, estimation) and NEVER tags owned by
siblings: position fix and bias tags of gnss-pseudorange-positioning
(pseudorange-positioning, gnss-position-fix, receiver-clock-bias,
ecef-position-solution, satellite-pseudorange-residual, snapshot-
navigation-solution), smoothing tags of gnss-carrier-smoothing
(carrier-phase-smoothing, hatch-filter-recursion, code-carrier-
divergence-monitor, smoothed-range-noise-reduction), integrity tags of
gnss-raim-fde (raim, fault-detection-and-exclusion, horizontal-
protection-level, chi-square-threshold, gnss-integrity) and the comm
doppler tags of space-systems/subsystems/doppler-shift (doppler-shift,
range-rate-frequency-offset, doppler-rate, acquisition-frequency-offset,
worst-case-doppler). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term (the banned word from the builder kit), action
verb present. Recommended wording (outputs in Claim order): "Use when
you must estimate the 3-D velocity of a GNSS receiver and its receiver
clock drift at a single epoch from carrier-phase delta-range-rate
(doppler) observables: propagate each satellite ECEF position and
velocity from the broadcast-ephemeris Kepler elements, form the
line-of-sight unit vector from the receiver position (pseudorange fix
first, or supplied), predict the range rate rho_dot = (v_sat - v_rec)
dot u + c*dt_dot, and solve the iterated least-squares system over the
per-satellite doppler residuals, rows [u, -1.0], by 4x4 normal
equations for the receiver velocity and clock drift. Produces the
velocity fix in m/s with the per-axis 1-sigma precision from the
doppler covariance, the recovered clock drift in m/s and s/s, the
post-fit residual RMS and the convergence state that gate the
navigation velocity output. Trigger: receiver velocity fix, doppler
positioning, carrier delta range rate, clock drift estimate, velocity
fix per-axis precision." The position-fix deliverables (x, y, z, clock
bias of the snapshot) and the comm frequency tokens must not appear.

FORBIDDEN TOKENS (belong to siblings): position-fix, receiver-clock-
bias, pseudorange-residual, position-solution, position-error,
geodetic-conversion (gnss-pseudorange-positioning); hatch-recursion,
smoothed-range, code-carrier-divergence, ionospheric-divergence,
smoothing-time-constant (gnss-carrier-smoothing); protection-level,
fault-detection, satellite-exclusion, chi-square, false-alarm,
integrity-monitoring (gnss-raim-fde); received-frequency,
delta-f-offset, s-band-downlink, acquisition-frequency,
worst-case-doppler, doppler-rate, overflight-model, circular-speed,
ground-elevation-angle (space-systems/subsystems/doppler-shift);
orbit-determination, gibbs-method (gnc-autonomy/space/
orbit-determination). The doppler leaf works in the range-rate domain in
m/s only; frequency-domain outputs are never computed.
