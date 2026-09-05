# Wave-40 leaf spec: magnetometer-calibration (space-systems, adcs pack)

- Path: skills/space-systems/adcs/magnetometer-calibration/
- Pack: adcs. Closest siblings: attitude-determination-triad (consumes two
  non-parallel measured BODY directions: its quick reference opens "TRIAD
  inputs: two non-parallel unit directions b1 and b2 measured in the body
  frame (for example a sun sensor and a magnetometer pair)" and its Pitfalls
  chain stops at star identification; zero estimation of the sensor error
  model itself), attitude-determination-quest (Davenport q-method over N
  weighted observations: "minimize the Wahba cost over N >= 2 weighted body
  and reference direction pairs"; takes the measured vectors as given),
  gyro-allan-variance (noise characterization of a RATE sensor: "categorize
  the noise process from the slope band" into angle-random-walk etc.; no
  bias/scale estimation), star-tracker (centroid and roll error model of a
  camera, no magnetometer content), magnetorquer-control (ACTUATOR only:
  "a magnetorquer (torque rod) is a coil that produces a magnetic dipole
  moment m (A m^2)" with the B-dot detumbling law and torque authority; the
  field B is an input, never calibrated here). Whole-tree greps at prep:
  "calibrat*" = 0 hits in skills/space-systems (re-verified); no leaf in
  space-systems/adcs estimates a magnetometer bias or scale vector, so
  every attitude consumer below treats raw sensor output as truth. GENUINE
  SPACE gap (fresh probe).
- Standards id: ecss (reference-only; adcs pack convention). Ledger Standard: ecss.
- Family: space-systems

## Claim

Estimate the in-flight magnetometer bias vector from scalar-checking batch
least squares: build the linear system from the measurement magnitudes
|m_k - b|^2 = B_k^2 against known field magnitudes B_k (the IGRF magnitude
at each sample, treated as an input), solve the 4-unknown normal equations
for x = [b_x, b_y, b_z, |b|^2] with a documented partial-pivot Gaussian
elimination, extract the bias from the first three unknowns, and report the
fourth-unknown consistency check |b|^2 against the recovered bias norm and
the fit residual. Produces the bias vector, the consistency gap and the
max residual that gate whether calibrated vectors can feed attitude
determination. Does NOT do: attitude determination from calibrated vectors
(TRIAD/QUEST, which consume the vectors this leaf cleans); gyro noise
characterization (gyro-allan-variance); star centroid matching
(star-tracker); dipole/B-dot actuation (magnetorquer-control). Scale
factors and cross-axis terms are a disclosed limitation: the scalar
checking model is encoded bias-only, because a clean linear encoding of the
3 diagonal scale unknowns turns the scalar-checking design nonlinear.

## Model (implement exactly)

Measurement model (bias only, noise-free in the synthetic fixtures): a
measured body-frame magnetometer sample m_k = h_k + b + noise, where h_k is
the true field vector over an attitude-diverse trajectory and |h_k| = B_k is
the known field magnitude at sample k (in nT). Scalar checking expands
|m_k - b|^2 = B_k^2 into |m_k|^2 - 2 m_k.b + |b|^2 = B_k^2, a LINEAR system
in the 4 unknowns x = [b_x, b_y, b_z, |b|^2] with rows
[-2*m_kx, -2*m_ky, -2*m_kz, 1] and right side y_k = B_k^2 - |m_k|^2.

Functions (pure stdlib):
- scalar_checking_design(measurements, field_magnitudes) -> (A, y): A is a
  list of 4-float rows as above, y the list of right sides. ValueError if
  the lists differ in length, if fewer than 4 measurements are given
  ("fewer than 4 measurements cannot constrain 4 unknowns"), or if any
  field magnitude is <= 0.
- solve_linear_system(matrix, vector) -> list of n unknowns: Gaussian
  elimination with partial pivoting for an n x n system; ValueError if the
  matrix is numerically singular (pivot below SINGULARITY_TOL relative to
  the largest matrix entry), message "insufficient attitude diversity".
- least_squares_solve(A, y) -> list of 4 unknowns: normal equations
  A^T A x = A^T y formed with plain matrix multiply, solved by
  solve_linear_system (so the rank check on A^T A is the diversity gate).
- residual_norm(A, y, x) -> float: max over samples of |(A x)_k - y_k|, the
  fit quality in nT^2.
- estimate_bias(measurements, field_magnitudes) -> dict with keys bias
  (3-tuple b_x, b_y, b_z), bias_norm_nt, expected_sq_norm (the fourth
  unknown x[3]), max_residual (residual_norm of the fit). Document that the
  fourth unknown is a consistency check: it must equal the recovered
  |b|^2.
- calibrate_measurement(m, b) -> tuple m - b elementwise; ValueError if the
  vector lengths differ.
Module constants: SINGULARITY_TOL = 1e-12. No other magic numbers.

Identities to test: on a noise-free synthetic set built from a known true
bias and 8+ diverse unit field directions with magnitudes 25000-45000 nT,
the recovered bias error is below 1e-6 nT, the fourth unknown equals
|b_true|^2 to float precision, the max residual is below 1e-6 nT^2, and
calibrate_measurement(m, b_hat) reproduces the true field vectors exactly;
measurements confined to one line give the "insufficient attitude
diversity" ValueError.

## Worked example

b_true = (200, -150, 300) nT. Ten deterministic unit directions (the three
axes, four body diagonals, (1, 0, 1)/sqrt(2), and (0.6, 0.8, 0)), field
magnitudes B_k = 30000 + 1500*k nT for k = 0..9 (30000 to 43500 nT), true
fields h_k = B_k * u_k, synthetic measurements m_k = h_k + b_true,
noise-free. Real module outputs (anchor script run at prep):

- Recovered bias: 200.000000, -150.000000, 300.000000 nT; bias error
  2.666e-12 nT (identity bound 1e-6 nT).
- Recovered |b| = 390.512484 nT; true |b| = 390.512484 nT.
- Fourth unknown x[3] = 152500.000000 nT^2; |b_true|^2 = 152500 nT^2;
  consistency gap 7.683e-8 nT^2.
- Max residual max_k |(A x - y)_k| = 1.527e-7 nT^2.
- calibrate_measurement on sample 4: (19918.584287, 19918.584287,
  19918.584287) nT against true field (19918.584287, 19918.584287,
  19918.584287) nT; max calibrate error over all 10 samples 3.779e-12 nT.
- Collinear fixture (all samples along one axis): ValueError "insufficient
  attitude diversity"; 3 samples: ValueError "fewer than 4 measurements
  cannot constrain 4 unknowns".
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (reproduced at prep with stdlib math).

## Validation list (contract test must include)

- estimate_bias on the worked-example fixture: recovered bias within 1e-6
  nT of (200, -150, 300); bias error below 1e-6 nT.
- Fourth unknown 152500.0 within 1e-4; consistency gap below 1e-3 nT^2.
- Max residual below 1e-3 nT^2 on the noise-free fixture.
- calibrate_measurement reproduces the true fields to below 1e-6 nT on all
  10 samples; error at the first sample below 1e-6.
- rotate the fixture: bias estimate is invariant under a fixed rotation of
  all measurement vectors and directions.
- ValueErrors: length mismatch, 3 measurements, field magnitude 0 or
  negative, collinear/planar-with-zero-rank fixtures ("insufficient
  attitude diversity"), calibrate_measurement length mismatch.
- Determinism: identical inputs give byte-identical outputs; dict keys
  exactly as documented.

## Corpus fragment (eval/hit1-wave40-magnetometer-calibration.yaml)

Query 1 (copy verbatim):
  "run the magnetometer-calibration scalar-checking batch least squares to estimate the magnetometer bias vector from the in-flight field-magnitude samples"
  intent: "space-systems; magnetometer bias estimation by scalar checking"
  expected_skill: "space-systems/adcs/magnetometer-calibration"
Query 2 (copy verbatim):
  "perform the in-flight bias-estimation for the adcs magnetometer and check the recovered bias-norm consistency against the field magnitudes"
  intent: "space-systems; bias vector and consistency residual of the magnetometer"
  expected_skill: "space-systems/adcs/magnetometer-calibration"
Task ids: w40-magnetometer-calibration-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the in-flight magnetometer
bias vector with scalar-checking batch least squares:" and include the
outputs in the Claim. First tag: magnetometer-calibration. Additional tags
ONLY: scalar-checking, bias-estimation, in-flight-bias-calibration,
hard-iron-offset-estimation, field-magnitude-consistency. NEVER single
generic words (magnetometer, bias, calibration, field, magnitude, sensor,
estimation, least-squares). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): triad, q-method, wahba,
attitude-matrix, rotation-angle (attitude-determination-triad/-quest);
allan-deviation, angle-random-walk, arw (gyro-allan-variance); centroid,
roll-error (star-tracker); b-dot, detumbling, dipole, torque-authority,
coil (magnetorquer-control).
