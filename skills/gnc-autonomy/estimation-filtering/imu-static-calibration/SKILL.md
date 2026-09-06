---
name: imu-static-calibration
description: "Use when you must calibrate an IMU from laboratory static test data: reduce the six-position accelerometer test, the mean specific force with each body axis held up and down against the known plus/minus 1 g references, to the per-axis bias and scale factor from the paired holds, and extend the least-squares fit over all six positions to the scale and misalignment sensitivity matrix; reduce the rate-table gyro test, the measured rates regressed on the commanded rates of each axis, to the per-axis gyro bias and scale factor. Produces the accelerometer bias vector and scale factors in m/s^2, the dimensionless misalignment matrix, the gyro bias in deg/s and scale factors, and the residual fit errors of both reductions, which gate the navigation error assessment. Trigger: imu static calibration, six position accelerometer test, rate table gyro calibration, accelerometer bias and scale factor, gyro bias and scale factor, misalignment matrix fit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: estimation-filtering
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: estimation-filtering
  tags: [imu-static-calibration, six-position-test, rate-table-calibration, accelerometer-bias-scale, residual-fit-error]
  version: 0.1.0
  author: AeroSkills
---

# IMU Static Calibration (gnc-autonomy/estimation-filtering/imu-static-calibration)

Use when the task is the static calibration of an IMU from laboratory
test data: level the sensor in the +g and the -g orientation on each
body axis for the six-position accelerometer test, take the mean
specific force of each static hold, and solve the per-axis bias and
scale factor from the paired +/- 1 g references, with the full
scale-plus-misalignment sensitivity matrix available from a
least-squares fit over all six positions against the known 1 g
directions; then spin the sensor about each body axis at commanded
rotation rates for the rate-table gyro test, regress the measured rate
on the commanded rate, and read the per-axis gyro bias as the intercept
and the scale factor as the slope of the linear fit. This leaf
implements both reductions in pure Python (math and random only),
deterministic for a fixed seed. It pairs with the estimation-filtering
pack and navigation siblings, whose filters consume calibrated
measurements, and it hands its coefficient set and residual fit errors
to the navigation error assessment that follows calibration.

## Domain quick reference

- Measurement model of a static hold: m_k = b + A*(f_k*G0), where f_k
  is the hold direction from the pinned fixture POSITIONS (g units), b
  the bias vector in m/s^2 and A the dimensionless 3x3 sensitivity
  matrix whose diagonal entries A_ii = s_i are the scale factors and
  whose off-diagonal entries are the cross-axis (misalignment)
  sensitivities.
- Fixture order: POSITIONS = ((1,0,0), (-1,0,0), (0,1,0), (0,-1,0),
  (0,0,1), (0,0,-1)), so the +g hold of axis i sits at index 2*i and the
  -g hold at 2*i+1, in the order +x, -x, +y, -y, +z, -z. G0 = 9.80665
  m/s^2 converts the 1 g references into specific-force units.
- Pair reduction per axis i: with plus = means[2*i][i] and minus =
  means[2*i+1][i], the +g and -g hold means of channel i, the scale
  factor is s_i = (plus - minus)/(2*G0) and the bias b_i = (plus +
  minus)/2 in m/s^2.
- Least-squares fit over all six positions: for each output channel c
  the design rows (f_k[0]*G0, f_k[1]*G0, f_k[2]*G0, 1) over the six
  holds are regressed through the normal equations (X^T X) q = X^T y
  solved by Gaussian elimination with partial pivoting. The coefficient
  triple is row c of A (A_cc is the scale factor) and the fourth
  coefficient is bias_c. Because the fixture sums each f_j to zero over
  the six holds, X^T X = diag(2*G0^2, 2*G0^2, 2*G0^2, 6) exactly, so
  the fit is always well posed: the LS diagonal equals the pair closed
  form within float noise and the LS off-diagonals are the cross-axis
  sensitivities.
- Rate-table regression per axis: measured_rate = s*commanded_rate + b,
  so the ordinary least-squares slope over the commanded rates is the
  dimensionless scale factor and the intercept is the gyro bias in
  deg/s.
- The diagonal pair model predicts channel i of hold k as b_i +
  s_i*f_k[i]*G0; its residual rms over all 18 measurements carries the
  cross-axis leakage the diagonal model cannot absorb, and the
  misalignment-aware LS residual rms drops once the off-diagonal terms
  absorb that leakage.
- Units: accelerometer bias in m/s^2, gyro bias in deg/s, both scale
  factor sets dimensionless, residual fit errors in the units of the
  fitted channels.
- ARP4754A frames the air-vehicle system context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Record the six-position-test static-hold campaign: level the sensor
   with each body axis held up and then down, and take the mean
   specific force of every static hold against the known plus/minus 1 g
   references (simulate_six_position_means generates a deterministic
   synthetic campaign from injected truth for validation, with
   per-sample Gaussian noise of standard deviation sigma and the
   caller-supplied integer seed).
2. Run the pair reduction to the accelerometer-bias-scale pair closed
   form with fit_accel_pair_bias_scale: the per-axis bias in m/s^2 and
   scale factor from the paired +g and -g holds, plus the diagonal
   model residual rms over all 18 measurements.
3. Fit the misalignment matrix by least squares over all six positions
   with fit_accel_misalignment_ls: the dimensionless 3x3 sensitivity
   matrix (scale factors on the diagonal, cross-axis sensitivities
   off-diagonal), the LS bias vector and the LS residual rms, which
   sits below the pair residual once the leakage terms are in the
   model.
4. Collect the rate-table-calibration runs: spin the sensor about each
   body axis at the commanded rotation rates and record the measured
   gyro rates (simulate_rate_table generates a deterministic synthetic
   run set from injected truth, noise sigma in deg/s).
5. Regress the gyro axes with fit_gyro_rate_table: per-axis scale
   factor (slope) and bias in deg/s (intercept) of the measured-on-
   commanded linear fit, with the per-axis residual rms in deg/s.
6. Read off the residual fit errors of both reductions and confirm the
   calibration: compare each residual rms against the noise level of
   the test campaign and run the contract test
   scripts/test_imu_static_calibration.py, whose assertions pin the
   worked example, the noise-free identities and every ValueError
   rejection.

## Worked example

Injected truth: accelerometer bias b = (0.0120, -0.0080, 0.0200) m/s^2
(about +1.22, -0.82 and +2.04 mg), scale s = (1.0020, 0.9980, 1.0010),
cross-axis truth rows (0.0012, -0.0009), (0.0015, 0.0006) and
(-0.0011, 0.0008), noise sigma 5.0e-4 m/s^2, seed 7. Gyro bias b =
(0.0500, -0.0300, 0.0200) deg/s (180, -108 and 72 deg/h), scale s =
(0.9985, 1.0010, 0.9995), noise sigma 5.0e-3 deg/s, seed 11. All values
below are the real module outputs.

- Simulated hold means (m/s^2, +g then -g in the order +x, -x, +y, -y,
  +z, -z): hold 0 (+x) (9.838135, 0.006966, 0.009100); hold 1 (-x)
  (-9.814421, -0.023175, 0.030681); hold 2 (+y) (0.024324, 9.779249,
  0.028364); hold 3 (-y) (0.000356, -9.794839, 0.012247); hold 4 (+z)
  (0.002341, -0.001688, 9.836710); hold 5 (-z) (0.021075, -0.014730,
  -9.797329).
- Pair reduction: bias = (0.01185726, -0.00779527, 0.01969062) m/s^2
  and scale = (1.00200151, 0.99800075, 1.00105737), recovered within
  (0.000143, 0.000205, 0.000309) m/s^2 and (0.000002, 0.000001,
  0.000057) of the injected truth. The diagonal model leaves the
  cross-axis leakage in the residual: rms 8.713e-3 m/s^2.
- Least-squares fit over all six positions: sensitivity matrix A =
  ((1.00200151, 0.00122200, -0.00095519), (0.00153675, 0.99800075,
  0.00066492), (-0.00110033, 0.00082171, 1.00105737)) with bias =
  (0.01196855, -0.00803632, 0.01996211) m/s^2 and residual rms
  2.375e-4 m/s^2, below the pair residual as the off-diagonal terms
  absorb the leakage. The LS scale diagonal equals the pair scale
  within 1e-6; cross-axis recovery errors ((0.000022, 0.000055),
  (0.000037, 0.000065), (0.000000, 0.000022)) sit within 2e-4 of the
  injected truth.
- Rate-table gyro: commanded rates per axis (deg/s) axis 0 (50, 30,
  10, -10, -30, -50), axis 1 (40, 25, 5, -5, -25, -40), axis 2 (45,
  20, 15, -15, -20, -45); measured axis 0 (49.96888, 30.00689,
  10.03997, -9.93757, -29.91164, -49.87533), axis 1 (40.01239,
  25.00049, 4.96892, -5.04146, -25.05147, -40.06763), axis 2
  (45.00517, 20.01491, 15.01199, -14.97387, -19.95715, -44.95894).
- Gyro regression: bias = (0.048534, -0.029794, 0.023685) deg/s and
  scale = (0.998506, 1.001011, 0.999550), recovered within (0.001466,
  0.000206, 0.003685) deg/s and (0.000006, 0.000011, 0.000050) of the
  injected truth; per-axis residual rms (0.004153, 0.004688, 0.005127)
  deg/s sits at the injected noise sigma.
- Read-off: the six holds recover the accelerometer bias to about
  0.03 mg and the scale factors to 6e-5, and the full least-squares fit
  pulls the residual rms from 8.7e-3 down to 2.4e-4 m/s^2 once the
  cross-axis terms (1 mg-class sensitivities) are in the model; the
  rate table recovers the gyro bias to 0.0037 deg/s (about 13 deg/h on
  the worst axis) and the scale factors to 5e-5 with residuals at the
  injected rate noise.

## Verification

- Confirm simulate_six_position_means with the worked-example truth
  returns the six hold means above within 1e-5 m/s^2, and that a
  same-seed repeat returns bit-identical tuples.
- Confirm fit_accel_pair_bias_scale returns the pair bias and scale
  above within 1e-5, and the diagonal-model rms_residual 8.713e-3
  within 1e-3 m/s^2.
- Confirm fit_accel_misalignment_ls returns the matrix rows and bias
  above within 1e-4 and 1e-5, with the LS residual rms 2.375e-4 within
  1e-4 and strictly below the pair residual.
- Confirm the noise-free identities: with sigma = 0.0 the pair and LS
  fits recover the injected bias, scale and cross-axis truth within
  1e-9, and the LS diagonal equals the pair scale within 1e-9.
- Confirm simulate_rate_table returns the measured axis rates above
  within 1e-4 deg/s, and fit_gyro_rate_table the gyro bias within 1e-4
  deg/s, scale within 1e-5 and rms_per_axis within 2e-3 of the injected
  noise sigma.
- Confirm every non-physical input raises ValueError: means of 5 holds
  or rows wider than 3 channels, negative or non-finite sigma,
  non-positive scale factors, a single commanded rate per axis,
  measured and commanded lists of unequal length, a constant commanded
  rate (singular regression), and non-finite means or rates.
- Run the contract test offline: python3
  scripts/test_imu_static_calibration.py (31 tests, deterministic, in
  under 20 seconds).

## Related leaves

- gnc-autonomy/estimation-filtering/complementary-filter: online gyro
  bias estimation inside a running attitude observer, the operational
  counterpart of this leaf's lab regression.
- gnc-autonomy/navigation/inertial-navigation: consumes the calibrated
  bias and drift inputs this leaf produces as coefficients.
- gnc-autonomy/navigation/kalman-filter-design: filter design that
  consumes the calibrated measurements and their residual fit errors.
- gnc-autonomy/estimation-filtering/extended-kalman-filter and the
  other recursive filters of this pack: downstream consumers of
  calibrated measurements.
- space-systems/adcs/gyro-allan-variance: noise characterization of the
  same sensor class, a separate step from static calibration.
- space-systems/adcs/magnetometer-calibration: the magnetometer
  counterpart calibrated against field magnitudes alone.
- flight-test-operations/planning/flight-test-instrumentation: the
  pre-test release and currency gate that decides whether an
  instrumented channel is current and fit to fly.

## Pitfalls

- Claiming noise characterization: a single unforced rate time series
  with no commanded rate reference cannot separate bias and scale
  factor; the rate-table runs need the commanded rates as the
  regression regressor.
- Fitting the pair model when misalignment is present: the diagonal
  pairs leave the cross-axis leakage in the residual (8.7e-3 m/s^2 on
  the worked example); the six-position least-squares fit is required
  to absorb it (2.4e-4 m/s^2).
- Confusing the pair closed form with the full fit: the pair scale
  s_i = (plus - minus)/(2*G0) uses only channel i of the two on-axis
  holds, so it is exact against cross-axis contamination of the
  on-axis channel but reports no misalignment terms at all.
- Treating the gyro residual rms as an error of the fit rather than of
  the data: the per-axis residual rms sits at the injected noise sigma
  of the rate table (about 5e-3 deg/s on the example), so a residual
  far above the noise level signals a rate reference problem, not a
  regression problem.
- Simulating with sigma but no seed: the reduction must be
  deterministic, so every simulation call fixes random.Random(seed)
  with a caller-supplied integer seed.
- Regressing an axis from a single commanded rate: the normal matrix
  is singular, so each axis needs at least two distinct commanded
  rates; a constant commanded rate fails the same singularity guard.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_imu_static_calibration.py

The test covers the six-position worked example (hold means within
1e-5 m/s^2 of the real module outputs), the pair reduction bias and
scale against the injected truth, the diagonal-model residual rms at
8.713e-3 m/s^2, the misalignment least-squares matrix and bias with
the LS residual rms 2.375e-4 m/s^2 strictly below the pair residual,
the LS diagonal equal to the pair scale within 1e-6, cross-axis
recovery within 2e-4, the noise-free recovery identities within 1e-9,
the rate-table measured runs and gyro regression with residual rms at
the injected noise, bit-identical same-seed determinism, the shared
normal-equations solver on closed-form lines, the pinned G0 and
fixture order, stdlib-only imports, and ValueError rejection of every
non-physical input listed in the spec (malformed means, negative sigma,
non-positive scale, under-sampled or constant commanded rates, length
mismatches, singular regressions, non-finite data).

## Compliance

- Standards referenced, not reproduced: ARP4754A frames the air-vehicle
  system context; the calibration relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
