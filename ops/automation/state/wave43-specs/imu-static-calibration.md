# Wave-43 leaf spec: imu-static-calibration (gnc-autonomy,
# estimation-filtering pack)

- Path: skills/gnc-autonomy/estimation-filtering/imu-static-calibration/
- Pack: estimation-filtering (present siblings alpha-beta-filter,
  complementary-filter, extended-kalman-filter,
  interacting-multiple-model-filter, particle-filter, rts-smoother,
  unscented-kalman-filter; adjacent fences in gnc-autonomy/navigation
  (inertial-navigation, navigation-frames, kalman-filter-design) and
  across domains in space-systems/adcs (gyro-allan-variance,
  magnetometer-calibration) and flight-test-operations/planning
  (flight-test-instrumentation)).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the reduction of laboratory static test data to an IMU coefficient
  set):
  - inertial-navigation (gnc-autonomy/navigation) assesses drift ERROR
    GROWTH: its description reads "estimate position error growth from
    accelerometer bias and gyro drift, check the Schuler period and
    the leveling response". Bias and drift are INPUTS there, consumed
    to propagate position error (double integration, cubic growth);
    the leaf never estimates them from test data and its worked
    content starts from given bias and drift values.
  - gyro-allan-variance (space-systems/adcs) is noise
    characterization, not static calibration: its description reads
    "compute the overlapping Allan deviation AD(tau) over a
    correlation-time grid ... categorize the noise process from the
    slope band ... extract the angle random walk coefficient in
    deg/sqrt(h)". A single unforced rate time series with no commanded
    rate reference cannot separate bias and scale factor; Allan
    variance needs no known input rate.
  - magnetometer-calibration (space-systems/adcs) is a different
    sensor against a magnitude-only reference: its description reads
    "estimate the in-flight magnetometer bias vector with
    scalar-checking batch least squares ... expand |m_k - b|^2 =
    B_k^2 over the measured body-frame samples m_k and the known
    field magnitudes B_k". Hard-iron offset of the magnetometer, no
    direction reference; the six-position test's +/- 1 g directions
    and the rate table's commanded rates exist only for the
    accelerometer and gyro triad.
  - flight-test-instrumentation (flight-test-operations/planning)
    owns the channel-release and calibration CURRENCY gate: its
    description reads "verify the recording, telemetry, pre-test
    calibration, and measurement uncertainty chain before the test.
    Applies the Nyquist criterion, sensor range checks, ADC
    quantization, and calibration currency to release an instrumented
    channel for flight". It decides whether an instrumented channel is
    CURRENT and fit to fly; it does not reduce calibration test data
    to coefficients.
  - navigation-frames (gnc-autonomy/navigation) is pure coordinate
    geometry: "transform geodetic latitude, longitude, and altitude on
    the WGS-84 ellipsoid into ECEF position, build the ECEF to NED
    rotation matrix", with no estimation step at all.
  - complementary-filter (this pack) owns ONLINE gyro bias estimation
    during operation: its description reads "integrate the rate gyro
    ... into a continuous, drift-free attitude quaternion estimate
    with online gyro bias estimation" driven by vector-measurement
    fusion; the corpus intent "gyro-bias-estimation from
    vector-measurement fusion" routes there. Its bias is a state of a
    running attitude observer, not a deterministic regression of lab
    holds against commanded references.
  - kalman-filter-design and the recursive filters of this pack
    (extended-kalman-filter, unscented-kalman-filter,
    particle-filter, interacting-multiple-model-filter,
    alpha-beta-filter, rts-smoother) CONSUME calibrated measurements;
    none of them produces a sensor coefficient set.
  Whole-tree greps at prep: the tokens "six-position" and "rate-table"
  return 0 file hits across skills/ (grep -rln empty), and each of
  imu-static-calibration, six-position-test, rate-table-calibration,
  accelerometer-bias-scale and gyro-bias-scale returns 0 matches in
  eval/hit1-corpus.yaml and in every eval/*.yaml fragment. GENUINE
  gap (fresh probe, GO): no leaf reduces six-position and rate-table
  lab data to IMU bias, scale factor and misalignment.
- Standards id: arp4754a (reference-only, present in standards-map.yaml;
  already the ledger id of kalman-filter-design and
  complementary-filter). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Estimate the static calibration coefficient set of an IMU from
laboratory test data: six-position accelerometer calibration (level
the sensor in the +g and the -g orientation on each body axis, take
the mean specific force of each static hold, and solve the per-axis
bias and scale factor from the paired +/- 1 g references, with the
full scale-plus-misalignment sensitivity matrix available from a
least-squares fit over all six positions against the known 1 g
directions) and rate-table gyro calibration (spin the sensor about
each body axis at commanded rotation rates, regress the measured rate
on the commanded rate, and read the per-axis gyro bias as the
intercept and the scale factor as the slope of the linear fit).
Produces the accelerometer bias vector (m/s^2) and dimensionless scale
factors, the dimensionless misalignment sensitivity matrix, the gyro
bias (deg/s) and scale factors, and the residual fit errors of both
reductions, which gate the navigation error analysis and filter
design. Does NOT do: inertial navigation drift error growth from
given bias and drift values, Schuler leveling or INS/GPS integration
(inertial-navigation); Allan deviation noise slopes, angle random
walk or bias instability (gyro-allan-variance); magnetometer hard or
soft iron offsets estimated against field magnitudes
(magnetometer-calibration); instrumented-channel release, calibration
currency or measurement uncertainty chains (flight-test-
instrumentation); ECEF/NED coordinate conversion (navigation-frames);
online in-flight gyro bias estimation by a Mahony attitude observer
(complementary-filter); filter design that consumes calibrated
measurements (kalman-filter-design and the recursive filters of this
pack). Deterministic least-squares reduction of static lab means
only: no time series dynamics, no strapdown propagation, no noise
characterization, no in-flight operation; accelerometer references at
exactly +/- 1 g and gyro references at the commanded rates.

## Model (implement exactly)

Pure stdlib: math and random only (no numpy, no scipy). Module
constants: G0 = 9.80665 m/s^2 (standard gravity) and the pinned
fixture POSITIONS = ((1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1),
(0,0,-1)) in g units: the +g hold of axis i sits at index 2*i and the
-g hold at 2*i+1, in the order +x, -x, +y, -y, +z, -z. All RNG use is
random.Random(seed) with the caller-supplied integer seed (defaults 7
and 11 in the worked example), so the reduction is deterministic and
bit-reproducible.

Defining relations (pin these exactly; every function below derives
from them):
- Measurement model of a static hold: m_k = b + A*(f_k*G0), where f_k
  is the hold direction from POSITIONS, b the bias vector in m/s^2
  and A the dimensionless 3x3 sensitivity matrix whose diagonal
  entries A_ii = s_i are the scale factors and whose off-diagonal
  entries are the cross-axis (misalignment) sensitivities.
- Pair reduction (per axis i): with plus = means[2*i][i] and minus =
  means[2*i+1][i], the +g and -g hold means of channel i, s_i =
  (plus - minus)/(2*G0) and b_i = (plus + minus)/2 in m/s^2. The
  diagonal model predicts channel i of hold k as b_i + s_i*f_k[i]*G0;
  its residual rms over all 18 measurements carries the cross-axis
  leakage the diagonal model cannot absorb.
- Least-squares fit over all six positions: for each output channel c
  build the design rows (f_k[0]*G0, f_k[1]*G0, f_k[2]*G0, 1) over the
  six holds and solve the normal equations (X^T X) q = X^T y by
  Gaussian elimination with partial pivoting; the coefficient triple
  is row c of A (A_cc is the scale factor) and the fourth coefficient
  is bias_c in m/s^2. Because the fixture sums each f_j to zero over
  the six holds, X^T X = diag(2*G0^2, 2*G0^2, 2*G0^2, 6) exactly and
  the fit is always well posed: the LS diagonal equals the pair
  closed form within float noise and the LS off-diagonals are the
  cross-axis sensitivities.
- Rate-table regression per axis: measured_rate = s*commanded_rate +
  b, so the ordinary least-squares slope over the commanded rates is
  the dimensionless scale factor and the intercept is the gyro bias
  in deg/s; residual rms per axis is reported against the fitted
  line.

Functions (8 total, all with docstrings, ValueError on non-physical
input; _check_3vec and _check_matrix3 are the finite/width guards):
- simulate_six_position_means(bias, scale, misalignment=None,
  sigma=0.0, seed=7) -> tuple of six 3-vectors in m/s^2: bias (m/s^2),
  scale (dimensionless, all positive), misalignment (optional 3x3
  off-diagonal truth, diagonal forced to scale), sigma the per-sample
  Gaussian noise in m/s^2. ValueError if bias or scale is not a
  3-vector of finite numbers, scale has a non-positive entry,
  misalignment is not a finite 3x3, or sigma is negative or
  non-finite.
- fit_accel_pair_bias_scale(means) -> dict with bias (tuple m/s^2),
  scale (tuple) and rms_residual (m/s^2) of the diagonal model over
  all 18 measurements. ValueError if means is not exactly 6 holds of
  3 finite numbers.
- fit_accel_misalignment_ls(means) -> dict with matrix (tuple of three
  row tuples, dimensionless), bias (tuple m/s^2) and rms_residual
  (m/s^2) over all 18 measurements. Same ValueError set.
- simulate_rate_table(commanded_by_axis, bias, scale, sigma=0.0,
  seed=7) -> tuple of three measured-rate tuples (deg/s):
  commanded_by_axis must hold at least 2 finite commanded rates on
  each of the 3 axes; bias in deg/s, scale dimensionless positive.
  ValueError if an axis has fewer than 2 commanded rates, the vectors
  are ill-formed, a scale factor is non-positive, a commanded rate is
  non-finite, or sigma is negative or non-finite.
- fit_gyro_rate_table(measured_by_axis, commanded_by_axis) -> dict
  with bias (tuple deg/s), scale (tuple) and rms_per_axis (tuple
  deg/s). ValueError if the shapes do not cover 3 axes or the
  measured and commanded lists differ in length per axis, an axis has
  fewer than 2 samples, or a measured rate is non-finite.
- ols_fit(design_rows, y) -> tuple of coefficients from the normal
  equations (X^T X) q = X^T y solved by Gaussian elimination with
  partial pivoting (shared by the misalignment fit and the gyro
  regression). ValueError if the design rows and y differ in length,
  a row width is inconsistent, y is non-finite, or the normal matrix
  is singular (a single distinct commanded rate per axis).
- _solve_linear_system(a, y) (private): partial-pivot elimination;
  ValueError on a singular matrix.
- _check_3vec(v, name) and _check_matrix3(m, name) (private guards).

Identities to test (deterministic):
- LS diagonal equals pair scale within float noise: within 1e-6 on
  the noisy worked example (real anchor True) and within 1e-9 when
  the fit is noise-free (real anchor True), because both reduce to
  the same +/- 1 g pair algebra.
- Noise-free recovery: with sigma = 0.0 the pair and LS fits return
  the injected bias, scale and cross-axis truth exactly (real anchor
  recovery errors print 0.000000000 at 9 decimals, well inside 1e-9).
- Residual ordering: the misalignment-aware LS residual rms sits
  strictly below the diagonal pairs residual rms on the same data
  (real anchor 2.375e-04 below 8.713e-03), the cross-axis leakage the
  pairs model leaves in the residual.
- Gyro residuals: per-axis residual rms of the worked example
  (0.004153, 0.004688, 0.005127) deg/s sits at the injected noise
  sigma of 5.0e-3 deg/s, the expected regression scatter.
- Determinism: two same-seed simulation runs return bit-identical
  tuples (real anchor True).
- ValueErrors across the module: means of 5 holds or 4-axis rows;
  negative sigma; non-positive scale; a single commanded rate per
  axis; measured/commanded length mismatch; a constant commanded rate
  (singular regression); non-finite measured means.
- No imports beyond math and random; G0 fixed at 9.80665; fixture
  order pinned as POSITIONS.

## Worked example

Injected truth: accelerometer bias b_true = (0.0120, -0.0080, 0.0200)
m/s^2 (about +1.22, -0.82 and +2.04 mg), scale s_true = (1.0020,
0.9980, 1.0010), cross-axis truth rows (0.0012, -0.0009), (0.0015,
0.0006) and (-0.0011, 0.0008), noise sigma 5.0e-4 m/s^2, seed 7.
Gyro bias b_true = (0.0500, -0.0300, 0.0200) deg/s (180, -108 and 72
deg/h), scale s_true = (0.9985, 1.0010, 0.9995), noise sigma 5.0e-3
deg/s, seed 11. All values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_imucal.py (stdlib math/random, exit 0).
- Measured mean specific force per hold (m/s^2), +g then -g on each
  axis in the order +x, -x, +y, -y, +z, -z: hold 0 (+x) (9.838135,
  0.006966, 0.009100); hold 1 (-x) (-9.814421, -0.023175, 0.030681);
  hold 2 (+y) (0.024324, 9.779249, 0.028364); hold 3 (-y) (0.000356,
  -9.794839, 0.012247); hold 4 (+z) (0.002341, -0.001688, 9.836710);
  hold 5 (-z) (0.021075, -0.014730, -9.797329).
- Pair reduction: bias = (0.01185726, -0.00779527, 0.01969062) m/s^2
  and scale = (1.00200151, 0.99800075, 1.00105737), recovered within
  (0.000143, 0.000205, 0.000309) m/s^2 and (0.000002, 0.000001,
  0.000057) of the injected truth. The diagonal model leaves the
  cross-axis leakage in the residual: rms 8.713e-03 m/s^2.
- Least-squares fit over all six positions: sensitivity matrix A =
  ((1.00200151, 0.00122200, -0.00095519), (0.00153675, 0.99800075,
  0.00066492), (-0.00110033, 0.00082171, 1.00105737)) with bias =
  (0.01196855, -0.00803632, 0.01996211) m/s^2 and residual rms
  2.375e-04 m/s^2, below the pair residual as the off-diagonal terms
  absorb the leakage. LS scale diagonal (1.00200151, 0.99800075,
  1.00105737) equals the pair scale within 1e-6; cross-axis recovery
  errors ((0.000022, 0.000055), (0.000037, 0.000065), (0.000000,
  0.000022)); tolerance verdicts bias within 2e-3 m/s^2, scale within
  1e-3 and cross-axis within 2e-4 all True.
- Rate-table gyro: commanded rates per axis (deg/s) axis 0 (50, 30,
  10, -10, -30, -50), axis 1 (40, 25, 5, -5, -25, -40), axis 2 (45,
  20, 15, -15, -20, -45); measured axis 0 (49.96888, 30.00689,
  10.03997, -9.93757, -29.91164, -49.87533), axis 1 (40.01239,
  25.00049, 4.96892, -5.04146, -25.05147, -40.06763), axis 2
  (45.00517, 20.01491, 15.01199, -14.97387, -19.95715, -44.95894).
  Regression: bias = (0.048534, -0.029794, 0.023685) deg/s and scale
  = (0.998506, 1.001011, 0.999550), recovered within (0.001466,
  0.000206, 0.003685) deg/s and (0.000006, 0.000011, 0.000050) of the
  injected truth; per-axis residual rms (0.004153, 0.004688,
  0.005127) deg/s at the injected noise sigma; tolerance verdicts
  bias within 2e-2 deg/s and scale within 5e-4 both True.
- Identities: same-seed repeat bit-identical True; noise-free pair
  bias, pair scale, LS bias and LS cross-axis recovery errors all
  print 0.000000000 at 9 decimals (within 1e-9); noise-free LS
  diagonal equals pair scale within 1e-9 True. All 8 ValueError cases
  raise (5-hold means, 4-axis rows, negative sigma, non-positive
  scale, one commanded rate per axis, measured/commanded mismatch,
  constant commanded rate, non-finite mean).
- Read-off: the six holds recover the accelerometer bias to about
  0.03 mg and the scale factors to 6e-5, and the full least-squares
  fit pulls the residual rms from 8.7e-3 down to 2.4e-4 m/s^2 once
  the cross-axis terms (1 mg-class sensitivities) are in the model;
  the rate table recovers the gyro bias to 0.0037 deg/s (about 13
  deg/h on the worst axis) and the scale factors to 5e-5 with
  residuals at the injected rate noise.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w43spec/anchor_imucal.py
(stdlib math/random, seeded, exit 0).

## Validation list (contract test must include)

- simulate_six_position_means((0.0120, -0.0080, 0.0200), (1.0020,
  0.9980, 1.0010), ((0.0, 0.0012, -0.0009), (0.0015, 0.0, 0.0006),
  (-0.0011, 0.0008, 0.0)), sigma = 5e-4, seed = 7) returns the six
  hold means of the worked example within 1e-5 m/s^2, and a same-seed
  repeat returns bit-identical tuples.
- fit_accel_pair_bias_scale on those means: bias (0.01185726,
  -0.00779527, 0.01969062) within 1e-5 m/s^2, scale (1.00200151,
  0.99800075, 1.00105737) within 1e-5; recovered bias within 1e-3
  m/s^2 and scale within 1e-3 of the injected truth; diagonal-model
  rms_residual 8.713e-3 within 1e-3 m/s^2.
- fit_accel_misalignment_ls on the same means: matrix rows
  (1.00200151, 0.00122200, -0.00095519), (0.00153675, 0.99800075,
  0.00066492) and (-0.00110033, 0.00082171, 1.00105737) within 1e-4;
  bias (0.01196855, -0.00803632, 0.01996211) within 1e-5 m/s^2; LS
  rms_residual 2.375e-4 within 1e-4 m/s^2 and strictly below the pair
  rms_residual; LS diagonal equals the pair scale within 1e-6; each
  recovered cross-axis entry within 2e-4 of the injected truth.
- Noise-free identity: with sigma = 0.0 the pair and LS fits recover
  the injected bias, scale and cross-axis truth within 1e-9, and the
  LS diagonal equals the pair scale within 1e-9.
- simulate_rate_table(((50, 30, 10, -10, -30, -50), (40, 25, 5, -5,
  -25, -40), (45, 20, 15, -15, -20, -45)), (0.05, -0.03, 0.02),
  (0.9985, 1.0010, 0.9995), sigma = 5e-3, seed = 11) returns the
  measured axis rates of the worked example within 1e-4 deg/s.
- fit_gyro_rate_table on those runs: bias (0.048534, -0.029794,
  0.023685) deg/s within 1e-4, scale (0.998506, 1.001011, 0.999550)
  within 1e-5; recovered bias within 2e-2 deg/s and scale within 5e-4
  of the injected truth; rms_per_axis (0.004153, 0.004688, 0.005127)
  each within 2e-3 of the injected sigma 5e-3 deg/s.
- ValueErrors: means of 5 holds or 4-axis rows; negative sigma;
  non-positive scale factor; one commanded rate per axis; measured
  and commanded lists of unequal length; a constant commanded rate
  per axis (singular regression through ols_fit); non-finite measured
  means or rates.
- Determinism; no imports beyond math and random; G0 = 9.80665; hold
  order pinned +x, -x, +y, -y, +z, -z.
- Contract test file named test_imu_static_calibration.py
  (underscores), unittest, offline in under 20 seconds.

## Corpus fragment (eval/hit1-wave43-imu-static-calibration.yaml)

Query 1 (copy verbatim):
  "reduce the six-position-test accelerometer holds and the
  rate-table-calibration gyro runs of an imu-static-calibration lab
  campaign to the per-axis bias and scale factors with the residual
  fit errors"
  intent: "gnc-autonomy; offline IMU static calibration reducing
  six-position accelerometer means against the known +/- 1 g
  references and rate-table gyro rates against the commanded rates to
  the per-axis bias and scale factors with the residual fit errors"
  expected_skill: "gnc-autonomy/estimation-filtering/
  imu-static-calibration"
Query 2 (copy verbatim):
  "recover the accelerometer-bias-scale and gyro bias and scale
  factor from six-position-test lab data and commanded
  rate-table-calibration runs, including the misalignment matrix fit
  over all six positions and the residual fit errors"
  intent: "gnc-autonomy; six-position and rate-table lab data
  reduction to the IMU accelerometer and gyro bias and scale factors,
  the cross-axis misalignment matrix from the least-squares fit over
  all six positions, and the residual fit errors"
  expected_skill: "gnc-autonomy/estimation-filtering/
  imu-static-calibration"
Task ids: w43-imu-static-calibration-1 and -2. Prep grep (run at spec
time): each of the tokens imu-static-calibration, six-position-test,
rate-table-calibration, accelerometer-bias-scale and gyro-bias-scale
returns 0 matches in eval/hit1-corpus.yaml and in every eval/*.yaml
fragment (grep -c 0, grep -l empty), and "six-position|rate-table"
returns 0 file hits across the whole skills tree, so the queries
above are collision-free; the only corpus bias content near this
domain is the inertial-navigation intent "position error growth from
accelerometer bias double integration" (drift propagation, not
estimation) and the complementary-filter intent
"gyro-bias-estimation from vector-measurement fusion" (online
attitude-observer bias), neither of which reduces static lab test
data.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must calibrate an IMU from
laboratory static test data:" and include the outputs in the Claim.
First tag: imu-static-calibration. Additional tags ONLY:
six-position-test, rate-table-calibration, accelerometer-bias-scale,
residual-fit-error. NEVER single generic words (imu, gyro,
accelerometer, bias, scale, calibration, misalignment, sensor,
inertial, fit, error) and NEVER a sibling token below. 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term (the banned
word from the builder kit), action verb present. Recommended wording
(outputs and verdict in Claim order, 148 words, 953 chars, verified):
"Use when you must calibrate an IMU from laboratory static test data:
reduce the six-position accelerometer test, the mean specific force
with each body axis held up and down against the known plus/minus 1 g
references, to the per-axis bias and scale factor from the paired
holds, and extend the least-squares fit over all six positions to the
scale and misalignment sensitivity matrix; reduce the rate-table gyro
test, the measured rates regressed on the commanded rates of each
axis, to the per-axis gyro bias and scale factor. Produces the
accelerometer bias vector and scale factors in m/s^2, the
dimensionless misalignment matrix, the gyro bias in deg/s and scale
factors, and the residual fit errors of both reductions, which gate
the navigation error assessment. Trigger: imu static calibration, six
position accelerometer test, rate table gyro calibration,
accelerometer bias and scale factor, gyro bias and scale factor,
misalignment matrix fit."
FORBIDDEN TOKENS (belong to siblings): schuler-period,
double-integration-position-error, gyro-drift-error-growth,
position-error-growth, gyrocompass-alignment, ins-gps-integration,
strapdown-mechanization (inertial-navigation); allan-deviation,
angle-random-walk, rate-random-walk, bias-instability, noise-slope,
arw-coefficient, deg-per-root-hour (gyro-allan-variance);
scalar-checking, hard-iron-offset, soft-iron, field-magnitude-
consistency, in-flight-magnetometer-bias (magnetometer-calibration);
channel-release, calibration-currency, anti-aliasing, nyquist,
measurement-uncertainty, data-acquisition, telemetry (flight-test-
instrumentation); ecef, ned, geodetic, gmst, earth-rotation,
coordinate-conversion (navigation-frames); mahony,
gyro-bias-estimation, vector-measurement-fusion, attitude-quaternion,
so3-attitude-observer (complementary-filter); kalman-gain,
innovation-variance, error-covariance, process-noise, recursive state
estimation (kalman-filter-design and the recursive filters of this
pack). The corpus fragments for imu-static-calibration carry no
drift, allan, magnetometer, channel-currency or filter-design
content.
