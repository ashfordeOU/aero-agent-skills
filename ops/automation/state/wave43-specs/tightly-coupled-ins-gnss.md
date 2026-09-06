# Wave-43 leaf spec: tightly-coupled-ins-gnss (gnc-autonomy,
# navigation pack)

- Path: skills/gnc-autonomy/navigation/tightly-coupled-ins-gnss/
- Pack: navigation (present siblings bearing-only-localization,
  dilution-of-precision, gnss-carrier-smoothing, gnss-pseudorange-
  positioning, gnss-raim-fde, inertial-navigation, ins-gnss-integrated-
  filter, kalman-filter-design, navigation-frames; wave-43 sibling
  gnss-doppler-velocity-positioning in the same pack; adjacent fences in
  gnc-autonomy/estimation-filtering/extended-kalman-filter and
  process-noise-discretization, gnc-autonomy/space/orbit-determination).
- Provenance: wave-43 probe receipt #3 (leaf-plan lines 45-49): INS
  error-state filter on raw pseudorange observables + clock states;
  ins-gnss-integrated-filter body declares raw-observable filtering out
  of scope (owner-declared gap); rtca-do-229 + arp4754a; LOW overlap;
  magnitude L, the largest leaf of the wave.
- Claim fences (quoted from the sibling frontmatter and body at prep;
  none of them runs an error-state filter on raw pseudorange
  observables):
  - ins-gnss-integrated-filter (this pack) OWNS the loosely coupled
    position-domain update: its description reads "Use when you must
    fuse INS and GNSS in a loosely coupled error-state integration
    filter: assemble the 5-state psi-angle error model of the horizontal
    INS drift from the specific forces, discretize it into the state
    transition matrix, predict the position, velocity and heading error
    states and their covariance between GNSS fixes, and apply the GNSS
    position measurement update that drives the estimated error state
    toward the innovation through the Kalman gain", and its quick
    reference fixes the update as "GNSS measurement update (position
    domain, loosely coupled): innovation = z - H*x with z = [dr_N,
    dr_E] the position error measurement and H the 2x5 observation
    matrix on the position channels". Its related leaves hand the fix
    source to gnss-pseudorange-positioning ("the fix source of the
    measurement update"). Its pitfalls carries the OWNER-DECLARED fence,
    verbatim: "Confusing the loosely coupled position-domain update with
    raw-observable (tightly coupled) filtering, which is out of scope
    for this leaf." That body statement is the declared gap this leaf
    fills: raw pseudorange observables, not the position fix.
  - gnss-pseudorange-positioning (this pack) OWNS the snapshot LS
    position solution: its description reads "compute a GNSS receiver
    position fix from pseudorange measurements: given satellite
    positions in ECEF and their pseudoranges (geometric range plus
    receiver clock bias), solve the four-unknown navigation equations
    for x, y, z and clock bias with an iterated least-squares
    adjustment", and its body states "The leaf is a snapshot solution:
    no smoothing, no dynamics model". Its geometry row is the
    measurement-model source for this leaf: "row i of H is
    [-(sx-rx)/range, -(sy-ry)/range, -(sz-rz)/range, 1]; the 1 is the
    clock-bias partial". This leaf needs the snapshot solution only as
    the measurement-aiding prior (the initial position estimate and the
    P0 position block of the filter); it does NOT re-derive a snapshot
    LS solver as a deliverable.
  - gnss-carrier-smoothing (this pack) OWNS carrier-phase smoothing:
    its description reads "smooth GNSS code pseudoranges with
    carrier-phase delta ranges before positioning: run the first-order
    Hatch recursion at a smoothing time constant ... and monitor the
    code-carrier ionospheric divergence", with "Continuous carrier
    phase between epochs is assumed; cycle-slip repair and integer
    ambiguity resolution are out of scope". This leaf consumes ONLY raw
    (unsmoothed) code pseudoranges: no carrier phase, no Hatch
    recursion, no smoothed ranges, no code-carrier divergence monitor.
  - gnss-doppler-velocity-positioning (wave-43 sibling spec, this pack)
    OWNS the snapshot velocity + clock-drift fix "from carrier
    delta-range-rate (doppler) observables by iterated least squares".
    In this leaf the velocity error and clock drift are estimated from
    the INS error propagation and the raw-pseudorange time history
    only; doppler and range-rate observables never enter.
  - gnss-raim-fde (this pack) OWNS integrity fault detection and
    exclusion on the pseudorange set; this leaf treats the measurement
    set as fault-free and produces no detection verdict, no protection
    level and no exclusion.
  - inertial-navigation (this pack) OWNS INS mechanization and drift
    error growth; this leaf consumes the INS reference trajectory
    (position and velocity per epoch) as a GIVEN input and never
    re-mechanizes the INS.
  - kalman-filter-design (this pack) owns the scalar single-axis
    recursion and the tags kalman-gain, innovation-variance and
    error-covariance; extended-kalman-filter and process-noise-
    discretization (estimation-filtering pack) own the nonlinear EKF
    machinery and the van Loan discrete Qd producer respectively. This
    leaf is the linear 8-state vector recursion on raw pseudoranges;
    it quotes no scalar tuning rules and derives no Qd.
  Whole-tree greps at prep: the four distinctive tokens
  tightly-coupled-ins-gnss, raw-pseudorange-update, ins-gnss-tight-
  coupling and clock-state-filter each return ZERO hits in
  eval/hit1-corpus.yaml (grep count 0 per token), ZERO hits across
  skills/ and eval/ (whole-tree grep count 0), and ZERO hits in the
  wave43-specs files written so far. GENUINE gnc-autonomy gap (fresh
  probe #3, GO 2): no leaf runs an INS error-state filter on raw
  pseudorange observables with clock states.
- Standards id: rtca-do-229 and arp4754a (both reference-only, present
  in standards-map.yaml at lines 303 and 38; RTCA MOPS and SAE ARP are
  proprietary, name + paraphrase only, no reproduced text). Ledger
  Standard: rtca-do-229, arp4754a.
- Family: gnc-autonomy

## Claim

Run a tightly coupled INS/GNSS integration: an INS error-state Kalman
filter updated on RAW pseudorange observables, in the simplified
fixed 8-state form the leaf plan mandates (3 position error states, 3
velocity error states, receiver clock bias in metres, receiver clock
drift in m/s; STATE_SIZE = 8), NOT a full 15-state INS: the dynamics
model is explicitly the constant-velocity-error, constant-drift form
dr += dv*dt, db += dd*dt between updates with no attitude error
states, no accelerometer or gyro bias states, no gravity or Coriolis
terms, no earth-rate coupling, and no INS mechanization (the INS
reference trajectory is a given input). Between measurement epochs the
filter propagates the error state and its covariance through the exact
8x8 transition matrix of that model; at each epoch it predicts each
satellite pseudorange from the inertial position estimate plus the
receiver clock bias state (the full propagated estimate), builds the
measurement matrix from the line-of-sight geometry rows and the unit
clock column, computes the pseudorange residuals (measured minus
predicted), performs the Kalman update on those residuals, and outputs
the corrected position and velocity (reference plus the estimated
corrections) and the clock bias and drift estimates. Produces the
propagated and corrected error state, the propagated and corrected
covariance, the per-epoch innovation vector of the raw-pseudorange
update, the corrected navigation solution, and the closed-form
geometry identities of the measurement matrix, in SI units, that gate
the tightly coupled navigation solution of a moving receiver. Does NOT
do: the loosely coupled position-domain measurement update on GNSS
position fixes with the psi-angle error model (ins-gnss-integrated-
filter, which declares raw-observable filtering out of scope in its own
body); the snapshot iterated least-squares position fix (gnss-
pseudorange-positioning, whose snapshot solution enters only as the
measurement-aiding prior of the initial position block); carrier-phase
smoothing, Hatch recursion, smoothed ranges or code-carrier divergence
monitoring (gnss-carrier-smoothing); velocity or clock drift from
doppler or range-rate observables (gnss-doppler-velocity-positioning);
RAIM fault detection and exclusion (gnss-raim-fde); INS mechanization
or drift-error growth models (inertial-navigation); the scalar
single-axis recursion or tuning rules (kalman-filter-design). Raw code
pseudoranges only, m satellites with m >= 4 per update epoch; fewer
than four satellites raises ValueError (stated simplification: aiding
through a partially observable set is out of scope). Deterministic,
offline, stdlib math only.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes. Deterministic: plain row-by-row accumulation in matrix
products, no generator-sum float reassociation, Gaussian elimination
with partial pivoting for the linear solves. Module name
tightly_coupled_ins_gnss, module constant STATE_SIZE = 8.

Conventions (pin exactly; every function below derives from these):
- ECEF frame, SI units. Clock states are in METRES and m/s, matching
  the family convention of gnss-pseudorange-positioning, so the
  measurement model needs no speed-of-light conversion: the clock
  column of the measurement matrix is exactly 1.0 on ranges in metres.
- State vector x = [drx, dry, drz, dvx, dvy, dvz, db, dd] (indices
  0-2 position error in m, 3-5 velocity error in m/s, 6 clock bias
  error in m, 7 clock drift error in m/s). x is the correction ADDED
  to the INS reference solution: corrected position
  r_hat = r_ref + dr, corrected velocity v_hat = v_ref + dv, corrected
  clock bias b_hat = b_ref + db, corrected clock drift d_hat =
  d_ref + dd. The reference (INS position/velocity per epoch) is a
  given input; the clock reference defaults to b_ref = d_ref = 0, so
  the clock states hold the total bias and drift. The filter is the
  open-loop error-state form: the estimated corrections are not fed
  back into the reference, and the corrected solution is re-derived as
  reference + x_hat at each epoch.
- Measurement model: measured pseudorange rho_i = |r_true - s_i| +
  b_true + n_i; predicted pseudorange rho_hat_i = |r_hat - s_i| +
  b_hat evaluated at the FULL propagated estimate r_hat = r_ref + dr,
  b_hat = b_ref + db. Innovation y_i = rho_meas,i - rho_hat_i.
- Measurement row i: the partial of the range equation with respect to
  the receiver position is the negated line of sight, so row i of the
  8-column measurement matrix is [-(sx-rx_hat)/rho_i,
  -(sy-ry_hat)/rho_i, -(sz-rz_hat)/rho_i, 0, 0, 0, 1, 0], the same
  geometry-row sign convention as gnss-pseudorange-positioning
  (negated receiver-to-satellite unit vector) extended to 8 columns,
  with the unit clock-bias column and zero velocity-error and
  clock-drift columns: a single-epoch raw pseudorange carries no
  velocity or drift information, so those states are observed only
  through the time propagation (stated assumption).
- Error dynamics over dt (exact under the constant-velocity-error,
  constant-drift model): dr(k+1) = dr(k) + dv(k)*dt, dv constant,
  db(k+1) = db(k) + dd(k)*dt, dd constant. The 8x8 transition Phi is
  the identity with dt on the dr-dv couplings (Phi[i][3+i] = dt for
  i = 0..2) and Phi[6][7] = dt.
- Process noise Q is a stated per-step diagonal (8 entries, all >= 0),
  added in the covariance propagation P_next = Phi*P*Phi^T + diag(q).
  Measurement noise R is the per-satellite variance list (diagonal,
  strictly positive entries).
- Kalman update: S = H*P*H^T + R (m x m), K = P*H^T*S^-1 solved by
  Gaussian elimination with partial pivoting (singular S raises
  ValueError), x_new = x + K*y, P_new = (I - K*H)*P symmetrized by
  averaging P_new = (P_new + P_new^T)/2.
- The run driver iterates over epochs: the first epoch is updated from
  the initial x0, p0 directly (no prior propagation); every later
  epoch first propagates the error state and covariance over dt from
  the previous epoch posterior, then predicts, then updates. All
  epochs of one profile share the satellite count m.

Functions (public API, 8):
- state_transition_matrix(dt) -> 8x8 list of lists, the exact Phi
  above. ValueError if dt is non-finite or <= 0.
- propagate_state(x, dt) -> length-8 list: dr += dv*dt for each axis
  and db += dd*dt. ValueError if x is not length 8, or dt non-finite
  or <= 0, or any x entry non-finite.
- propagate_covariance(p, q, dt) -> 8x8 list of lists,
  Phi*P*Phi^T + diag(q) with q the length-8 diagonal. ValueError if p
  is not 8x8, q not length 8, any q entry negative or non-finite, or
  dt non-finite or <= 0.
- predicted_pseudoranges(sat_positions, ref_position, ref_bias) ->
  list of m ranges |r - s_i| + b. ValueError on an empty satellite
  list, non-length-3 position records, or non-finite entries.
- measurement_matrix(sat_positions, ref_position) -> m x 8 list of
  lists, rows as pinned above. ValueError if fewer than 4 satellites,
  ref_position not length 3, or a satellite within 1e-3 m of the
  receiver (zero range).
- kalman_update(x, p, h, innovations, variances) -> (x_new, p_new, k)
  tuple, the update pinned above; innovations length m and variances
  length m. ValueError on any shape mismatch (x not 8, p not 8x8, h
  rows not 8, empty h, innovation or variance length != m), a
  non-positive or non-finite variance, a non-finite innovation, or a
  singular innovation covariance S.
- corrected_navigation_state(ref_position, ref_velocity, ref_bias,
  ref_drift, x) -> dict with keys x, y, z, vx, vy, vz, bias, drift
  (each reference component plus the matching state correction).
  ValueError on non-length-3 reference records or x not length 8.
- run_tightly_coupled_profile(epochs, x0, p0, q, dt, variances) ->
  list of per-epoch result dicts, each carrying x_pred, p_pred,
  innovations, innovation_rms (sqrt of the mean squared innovation),
  x_corr, p_corr and corrected (the corrected_navigation_state dict).
  Each epoch dict carries sat_positions, pseudoranges, ref_position,
  ref_velocity, ref_bias and ref_drift. ValueError if the epoch list
  is empty, x0 not length 8, p0 not 8x8, q not length 8, the epoch
  satellite count is below 4, any epoch measurement count differs from
  the first, or variances do not match the count.

Private helpers (module-internal): _matmul (plain accumulated
row-by-row product), _transpose, _identity, _matvec, _solve (Gaussian
elimination with partial pivoting; pivot below 1e-300 raises
ValueError), _symmetrize.

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- Phi structure: state_transition_matrix(1.0) row 0 equals
  [1, 0, 0, 1, 0, 0, 0, 0] and row 6 equals [0, 0, 0, 0, 0, 0, 1, 1]
  (real anchor, exact to 0.000e+00).
- propagate_state closed form: a state with dr = (1, -2, 3), dv =
  (0.5, 0.25, -0.1), db = 10, dd = 2 at dt = 2 gives dr = (2, -1.5,
  2.8), db = 14 (assert within 1e-12).
- propagate_covariance matches the inline Phi*P*Phi^T + diag(q)
  product computed in the test to within 1e-9 relative.
- Measurement rows: on the worked constellation at the epoch-0
  reference the sat +x row starts -0.9999999999591737 (within 1e-6 of
  -1, the negated line of sight) and the sat -y row has its second
  entry 0.9999999999764121 (within 1e-6 of +1); cross-axis entries are
  of order 1e-5; the clock column is exactly 1.0 and the velocity and
  drift columns exactly 0.0 (real anchor).
- Predicted ranges: predicted_pseudoranges on the epoch-0 INS
  reference with zero clock bias returns [26559888.0011, 26560112.0011,
  26559808.0006, 26560192.0006, 26560144.0009, 26559856.0009] (within
  0.01 m per entry); the measured pseudorange of sat1 at epoch 0 is
  26561400.201177 m.
- Epoch-0 posterior covariance closed forms of the symmetric 6-sat
  geometry: per-axis position variance 0.124844 equals sigma^2/2
  within 1e-3 (two satellites per axis, sigma_range = 0.5 m,
  R = 0.25) and clock-bias variance 0.0416667 equals sigma^2/6 within
  1e-4 (six satellites): real anchor P diag 1.24844e-01 and
  4.16667e-02.
- Perfect-measurement identity (noise offsets zero, variances 1e-9):
  the epoch-0 update recovers the true corrections: dr = (-12.000002,
  8.000000, -6.000004) m against (-12, 8, -6) within 1e-3 and db =
  1500.000007 m against 1500 within 1e-3, and the epoch-2 estimates
  land at dv = (-0.497630, 0.298579, -0.199051) m/s against (-0.5,
  0.3, -0.2) within 0.01 and dd = 4.999935 m/s against 5.0 within
  0.01 (real anchor; the residual offset comes from the linearization
  of the range model about the propagated estimate).
- P symmetry: max |P - P^T| equals 0.00e+00 on every epoch posterior
  (real anchor), assert below 1e-12.
- Determinism: two identical profile runs bitwise identical.
- ValueErrors across the module: dt at 0.0 and -1.0 on
  state_transition_matrix, propagate_state and propagate_covariance;
  x of length 7; p of wrong shape; negative q entry; empty satellite
  list; satellite records of wrong length; fewer than 4 satellites;
  a satellite coincident with the receiver; a non-positive variance; an
  innovation/variance length mismatch; an epoch profile with 3
  satellites.
- Determinism; no imports beyond math; no RNG anywhere.

## Worked example

Scenario (all values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_tight.py, stdlib math, exit 0, all checks passed):
dt = 1.0 s; 3 epochs at t = 0, 1, 2 s; 6 satellites fixed on the
documented test constellation at radius R_S = 26560000.0 m along the
+-x, +-y and +-z ECEF axes (the same documented-test-constellation
convention as the gnss-pseudorange-positioning worked example, receiver
near the origin, satellite motion neglected over the 2 s window).
True receiver motion r_true(t) = (100 + 25 t, 200 - 10 t, -150 + 5 t)
m, v_true = (25, -10, 5) m/s; true clock b_true(t) = 1500 + 5 t m,
d_true = 5.0 m/s. The INS reference starts offset by e_p0 = (12, -8,
6) m and runs with the constant velocity error e_v = (0.5, -0.3, 0.2)
m/s, so the true INS position error grows from (12, -8, 6) to (13,
-8.6, 6.4) m over the run; the clock reference is zero, so the clock
states hold the totals. Raw pseudoranges are generated from the true
position plus the true clock bias plus the small fixed documented
noise realization (m, zero sum per epoch): epoch 0 [+0.2, -0.1, +0.3,
-0.2, +0.1, -0.3], epoch 1 [-0.1, +0.2, -0.2, +0.3, -0.3, +0.1],
epoch 2 [+0.3, +0.1, -0.1, -0.3, +0.2, -0.2]. Measurement variance
0.25 per satellite (sigma_range = 0.5 m). Initial state x0 = 0, P0 =
diag(100, 100, 100, 1, 1, 1, 2.5e7, 400) (position sigma 10 m from the
snapshot-fix measurement-aiding prior, velocity sigma 1 m/s, clock
bias sigma 5000 m, drift sigma 20 m/s), Q = diag(0.01, 0.01, 0.01,
0.001, 0.001, 0.001, 0.01, 1e-4).

- Measurement model anchors: predicted ranges from the epoch-0 INS
  reference (b = 0) are [26559888.0011, 26560112.0011, 26559808.0006,
  26560192.0006, 26560144.0009, 26559856.0009] m; the measured
  pseudorange of sat1 (at +x) at epoch 0 is 26561400.201177 m
  (geometric range about R_S - 100 m plus the 1500 m bias plus the
  +0.2 m offset).
- Epoch 0 (t = 0, no prior propagation; the first snapshot): the
  innovations carry the whole unknown clock bias plus the 12 m INS
  position offset projected on the lines of sight: [1512.2001,
  1487.9001, 1492.3000, 1507.8000, 1506.1000, 1493.7000] m,
  innovation RMS 1500.0274 m. The update lands the error state at
  x_corr = (-12.1348, 7.7403, -6.1923, 0, 0, 0, 1500.0000, 0): the
  position correction matches the negated INS offset and the clock
  bias estimate is 1500.0000 m (bias error +0.0000 m). The velocity
  and drift states stay zero: a single snapshot carries no velocity or
  drift information (their Kalman gain rows are exactly zero before
  any propagation). Corrected position (99.8652, 199.7403, -150.1923)
  m, 3D error 0.3501 m against the truth; corrected velocity
  (25.5000, -10.3000, 5.2000) m/s still carries the 0.5 m/s INS
  velocity error (3D error 0.6164 m/s); drift estimate 0 against the
  true 5.0 m/s. Posterior covariance diagonal: per-axis position
  1.24844e-01 (sigma 0.35 m, the R/2 closed form), velocity 1.0
  (unobservable), clock bias 4.16667e-02 (sigma 0.20 m, the R/6
  closed form), drift 4.00000e+02 (unobservable).
- Epoch 1 (t = 1 s; the error state and covariance are propagated
  over dt = 1 s, then the update runs): the propagation carries the
  position correction forward but the velocity error is still unknown,
  and the propagated bias (1500 m) cannot know the 5 m drift growth,
  so the innovations are the residuals of that shortfall: [5.2652,
  4.8348, 4.2403, 5.8597, 4.7077, 5.0923] m, RMS 5.0251 m (down from
  1500.03 m once the bias is known). The epoch-1 update corrects the
  position to (-12.3287, 8.4697, -6.0191), pulls the velocity
  correction to (-0.1708, 0.6427, 0.1526) m/s, the bias to 1504.9995
  m (error -0.0005 m) and the drift to 4.9988 m/s (error -0.0012
  m/s): the propagation-induced bias-drift and position-velocity
  correlations make the second snapshot observe both channels.
  Corrected position (125.1713, 190.1697, -144.8191) m, 3D error
  0.3015 m; corrected velocity (25.3292, -9.6573, 5.3526) m/s, 3D
  error 0.5917 m/s (the y-axis velocity estimate overshoots the true
  correction before the third snapshot refines it). Posterior
  diagonal: velocity 2.07251e-01 (sigma 0.46 m/s), drift 9.34116e-02
  (sigma 0.31 m/s).
- Epoch 2 (t = 2 s): the drift estimate now predicts the bias growth,
  so the innovations collapse to the measurement noise level: [0.8022,
  -0.3989, 0.4140, -0.8107, 0.7352, -0.7318] m, RMS 0.6717 m. Final
  error state x_corr = (-12.9851, 8.6172, -6.4596, -0.4525, 0.3554,
  -0.1915, 1509.9997, 4.9997), against the true corrections (-13.0,
  8.6, -6.4) m, (-0.5, 0.3, -0.2) m/s, 1510.0 m and 5.0 m/s.
  Corrected position (150.0149, 180.0172, -140.0596) m, 3D error
  0.0638 m; corrected velocity (25.0475, -9.9446, 5.0085) m/s, 3D
  error 0.0735 m/s; clock bias 1509.9997 m (error -0.0003 m); clock
  drift 4.9997 m/s (error -0.0003 m/s). Posterior diagonal: position
  1.01082e-01, velocity 6.44799e-02 (sigma 0.25 m/s), bias
  3.52379e-02, drift 2.59567e-02 (sigma 0.16 m/s).
- Convergence read-off: 3D position error 0.3501 -> 0.3015 -> 0.0638
  m and 3D velocity error 0.6164 -> 0.5917 -> 0.0735 m/s, decreasing
  every epoch; the clock bias lands within 0.001 m and the clock drift
  within 0.001 m/s of the truth by epoch 2. The innovation RMS tells
  the observability story: 1500.03 m at the first snapshot (unknown
  clock bias), 5.03 m at the second (the drift that one snapshot
  cannot see), 0.67 m at the third (measurement noise floor).
- Perfect-measurement identity run (noise offsets zero, variances
  1e-9): the epoch-0 update recovers dr = (-12.000002434, 8.000000468,
  -6.000003825) m and db = 1500.000006620 m; the epoch-2 estimates
  are dv = (-0.497630302, 0.298578652, -0.199050771) m/s and dd =
  4.999934518 m/s. Determinism: two identical profile runs are
  bitwise identical; P symmetry max |P - P^T| is 0.00e+00 on every
  epoch posterior.
Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w43spec/anchor_tight.py (stdlib math, Gaussian elimination,
exit 0).

## Validation list (contract test must include)

- state_transition_matrix(1.0): row 0 = [1, 0, 0, 1, 0, 0, 0, 0] and
  row 6 = [0, 0, 0, 0, 0, 0, 1, 1] within 1e-12; propagate_state on
  the closed-form spot check within 1e-12.
- propagate_covariance equals the inline Phi*P*Phi^T + diag(q) product
  within 1e-9 relative (assert with isclose or delta, NEVER exact
  equality).
- measurement_matrix on the worked constellation: sat +x first entry
  within 1e-6 of -1, sat -y second entry within 1e-6 of +1, clock
  column exactly 1.0, velocity and drift columns 0.0 (anchor
  -0.9999999999591737 and 0.9999999999764121).
- predicted_pseudoranges epoch-0 anchors within 0.01 m per entry;
  measured sat1 pseudorange 26561400.201177 m within 0.01 m.
- Worked example: innovations per epoch within 0.01 m of the anchors
  (epoch 0 [1512.2001, 1487.9001, 1492.3000, 1507.8000, 1506.1000,
  1493.7000], epoch 1 [5.2652, 4.8348, 4.2403, 5.8597, 4.7077,
  5.0923], epoch 2 [0.8022, -0.3989, 0.4140, -0.8107, 0.7352,
  -0.7318]); innovation RMS 1500.0274, 5.0251 and 0.6717 m within
  0.01 m.
- Error-state anchors: epoch-0 x_corr position correction (-12.1348,
  7.7403, -6.1923) with velocity and drift exactly 0 and db =
  1500.0000 within 0.01; epoch-2 x_corr (-12.9851, 8.6172, -6.4596,
  -0.4525, 0.3554, -0.1915, 1509.9997, 4.9997) within 0.01 per entry;
  the higher-precision epoch-2 values (-12.985090, 8.617167,
  -6.459646), (-0.452525, 0.355417, -0.191508), db = 1509.999739 and
  dd = 4.999677 within 0.01.
- Convergence: corrected position within 0.5 m 3D of the truth at
  every epoch (anchor errors 0.3501, 0.3015, 0.0638 m), corrected
  velocity within 0.8 m/s 3D at every epoch (anchor errors 0.6164,
  0.5917, 0.0735 m/s, epoch 2 below 0.1 m/s), clock bias within 0.5 m
  of the truth at every epoch from epoch 1 (anchor errors -0.0005 and
  -0.0003 m) and clock drift within 1.0 m/s at epochs 1 and 2 (anchor
  errors -0.0012 and -0.0003 m/s).
- Perfect-measurement identity: epoch-0 dr within 1e-3 of (-12, 8,
  -6) and db within 1e-3 of 1500 (anchor -12.000002434, 8.000000468,
  -6.000003825, 1500.000006620); epoch-2 dv within 0.01 of (-0.5,
  0.3, -0.2) and dd within 0.01 of 5.0 (anchor -0.497630302,
  0.298578652, -0.199050771, 4.999934518).
- Covariance: P symmetry max |P - P^T| below 1e-12 per epoch (anchor
  0.00e+00); epoch-0 posterior per-axis position variance within 1e-3
  of sigma^2/2 = 0.125 (anchor 1.24844e-01) and clock-bias variance
  within 1e-4 of sigma^2/6 = 0.0416667 (anchor 4.16667e-02);
  epoch-2 velocity variance 6.44799e-02 and drift variance
  2.59567e-02 within 1e-3.
- Determinism: two identical profile runs bitwise identical; no
  imports beyond math; no RNG.
- ValueErrors: dt at 0.0 and -1.0 on state_transition_matrix,
  propagate_state and propagate_covariance; x of length 7 on
  propagate_state and kalman_update; negative q entry; empty satellite
  list; a satellite record of length 2; measurement_matrix with 3
  satellites; a satellite coincident with the receiver; a zero
  variance on kalman_update; an innovation length mismatch; a profile
  whose epoch carries 3 satellites.
- Run the contract test under both python3 (3.9.x) and the pyenv 3.13
  hook interpreter; all asserts above are tolerance-based and must hold
  on both.

## Corpus fragment (eval/hit1-wave43-tightly-coupled-ins-gnss.yaml)

Query 1 (copy verbatim):
  "run the tightly-coupled-ins-gnss filter on raw pseudoranges:
  propagate the ins error states of position and velocity error plus
  the receiver clock bias and drift between epochs, predict each
  satellite pseudorange from the inertial position estimate and the
  clock bias state, build the measurement matrix from the line of
  sight geometry and the clock column, and apply the raw-pseudorange-
  update Kalman correction on the residuals"
  intent: "gnc-autonomy; 8-state INS error-state Kalman filter updated
  on raw pseudorange observables with the LOS geometry measurement
  matrix, the unit clock column and the clock bias and drift states"
  expected_skill: "gnc-autonomy/navigation/tightly-coupled-ins-gnss"
Query 2 (copy verbatim):
  "estimate the receiver clock bias and clock drift with a clock-
  state-filter inside an ins-gnss-tight-coupling filter that updates
  on raw pseudoranges, and check the corrected position, velocity and
  clock estimates against the true trajectory of a moving receiver"
  intent: "gnc-autonomy; clock-state-filter estimation of the receiver
  clock bias and drift within the tightly coupled INS/GNSS raw
  pseudorange update with corrected position and velocity outputs"
  expected_skill: "gnc-autonomy/navigation/tightly-coupled-ins-gnss"
Task ids: w43-tightly-coupled-ins-gnss-1 and -2. Prep grep:
tightly-coupled-ins-gnss, raw-pseudorange-update, ins-gnss-tight-
coupling and clock-state-filter appear in NO existing eval/hit1-
corpus.yaml task (grep count 0 per token), in NO skill file (whole-tree
count 0) and in NO wave43-specs file written so far; the
ins-gnss-integrated-filter tasks route on the psi-angle loosely coupled
position update, drift correction and heading error, the pseudorange
tasks route on the snapshot iterated least-squares fix of x, y, z and
clock bias, the carrier-smoothing tasks route on the Hatch recursion
and code-carrier divergence, and the doppler tasks route on the
carrier delta-range-rate velocity fix, so the queries above are
collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run a tightly-coupled-ins-gnss
integration filter:" and include the outputs in the Claim. First tag:
tightly-coupled-ins-gnss. Additional tags ONLY: raw-pseudorange-update,
ins-gnss-tight-coupling, clock-state-filter, pseudorange-los-geometry,
ins-error-state-ekf. NEVER single generic words (position, velocity,
clock, bias, drift, filter, pseudorange, geometry, covariance,
innovation, integration alone) and NEVER the sibling-owned compounds:
psi-angle-model, error-state-filter, loosely-coupled-integration,
gnss-position-update, ins-drift-correction, horizontal-specific-force,
heading-error, state-transition-matrix (ins-gnss-integrated-filter);
snapshot-navigation-solution, iterated-least-squares-fix,
ecef-position-solution, receiver-clock-bias (gnss-pseudorange-
positioning, which owns the plain receiver clock bias tag);
carrier-phase-smoothing, hatch-filter-recursion, code-carrier-
divergence-monitor, smoothed-range-noise-reduction (gnss-carrier-
smoothing); doppler, range-rate, carrier-delta-range-rate (gnss-
doppler-velocity-positioning); receiver-autonomous-integrity-
monitoring, protection-level, fault-detection (gnss-raim-fde);
van-loan-discretization, continuous-spectral-density,
discrete-noise-covariance (process-noise-discretization);
kalman-gain, innovation-variance, error-covariance (kalman-filter-
design). 50-150 words, <=1000 chars, no em dash, no content-policy
sweep term, action verb present. Recommended wording (outputs in Claim
order): "Use when you must run a tightly-coupled-ins-gnss integration
filter: propagate the eight ins error states (3 position error, 3
velocity error, receiver clock bias in metres and clock drift in m/s)
of the stated constant-velocity error model between epochs, predict
each raw pseudorange from the inertial position estimate plus the
clock bias state, build the measurement matrix from the line-of-sight
geometry rows and the unit clock column, and apply the raw-pseudorange-
update Kalman correction on the residuals. Produces the corrected
position and velocity of the receiver, the clock-state-filter estimates
of clock bias and drift, the per-epoch innovation vector and the
propagated and corrected covariance, in SI units, that gate the tightly
coupled navigation solution of a moving receiver. Trigger: tightly
coupled INS GNSS, raw pseudorange measurement update,
ins-gnss-tight-coupling, clock-state-filter, raw pseudorange Kalman
filter, INS error state with clock bias and drift." The sibling phrase
triggers "loosely coupled", "position-domain update", "snapshot
solution", "iterated least squares", "carrier smoothing", "Hatch" and
"doppler" must not appear as routing keywords.

FORBIDDEN TOKENS (belong to siblings): psi-angle model, loosely
coupled integration, gnss position update, ins drift correction,
heading error, horizontal specific force, the tag error-state-filter
(ins-gnss-integrated-filter); snapshot navigation solution, iterated
least squares fix, ecef position solution, the tag receiver-clock-bias
(gnss-pseudorange-positioning); carrier phase, hatch recursion,
code-carrier divergence, smoothed range, ionospheric divergence
(gnss-carrier-smoothing); doppler, range rate, delta-range-rate
(gnss-doppler-velocity-positioning); raim, fault detection and
exclusion, protection level (gnss-raim-fde); van loan, spectral
density, discrete noise covariance (process-noise-discretization);
kalman gain, innovation variance, error covariance, single-axis
recursion (kalman-filter-design); ins mechanization, specific-force
integration, attitude error, gyro bias, accelerometer bias (inertial-
navigation, and the full 15-state INS model, stated out of scope).
