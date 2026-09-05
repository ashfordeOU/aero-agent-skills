---
name: magnetometer-calibration
description: "Use when you must estimate the in-flight magnetometer bias vector with scalar-checking batch least squares: expand |m_k - b|^2 = B_k^2 over the measured body-frame samples m_k and the known field magnitudes B_k, build the 4-unknown rows [-2 m_k, 1] with right sides B_k^2 - |m_k|^2, solve the normal equations A^T A x = A^T y by partial-pivot Gaussian elimination, and recover the bias from the first three unknowns with the fourth unknown |b|^2 as the consistency check. Produces the bias vector, the consistency gap against the recovered bias norm, the max fit residual, and the calibrated samples that gate attitude determination. Trigger: magnetometer calibration, scalar checking, in-flight bias estimation, hard-iron offset, field magnitude consistency."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [magnetometer-calibration, scalar-checking, bias-estimation, in-flight-bias-calibration, hard-iron-offset-estimation, field-magnitude-consistency]
  version: 0.1.0
  author: AeroSkills
---

# Magnetometer Calibration (space-systems/adcs/magnetometer-calibration)

Use when the task is estimating the in-flight magnetometer bias
vector from the measurement magnitudes alone: scalar-checking batch
least squares solves for the hard-iron offset b from the field
magnitude constraints |m_k - b|^2 = B_k^2, where m_k is the raw
body-frame sample and B_k is the known field magnitude (the IGRF
magnitude at each sample, treated as an input, in nT). The estimate
dict, the consistency gap, and the fit residual gate whether cleaned
vectors may feed attitude determination. It pairs with
attitude-determination-triad and attitude-determination-quest, which
consume measured directions as given: TRIAD takes two non-parallel
measured body directions and QUEST minimizes the Wahba cost over N
weighted observation pairs, and neither estimates the sensor error
model itself. Out of scope: attitude determination from calibrated
vectors (the TRIAD and QUEST leaves); noise characterization of a rate
sensor (gyro-allan-variance); star centroid matching (star-tracker);
and magnetic actuation (magnetorquer-control, where the field is an
input and never calibrated). Scale factors and cross-axis terms are a
disclosed limitation of this leaf: the scalar-checking model is
encoded bias-only, because a clean linear encoding of the three
diagonal scale unknowns turns the scalar-checking design nonlinear.

## Domain quick reference

- Measurement model: m_k = h_k + b, with |h_k| = B_k the known
  field magnitude at sample k (nT). The scalar-checking identity
  |m_k - b|^2 = B_k^2 expands to |m_k|^2 - 2 m_k.b + |b|^2 = B_k^2, a
  LINEAR system in the four unknowns x = [b_x, b_y, b_z, |b|^2].
- Design row and right side per sample:
  [-2*m_kx, -2*m_ky, -2*m_kz, 1] and y_k = B_k^2 - |m_k|^2.
- Batch least squares: the normal equations A^T A x = A^T y are
  formed with plain matrix multiply and solved by Gaussian
  elimination with partial pivoting. A pivot below SINGULARITY_TOL =
  1e-12 relative to the largest matrix entry raises "insufficient
  attitude diversity": the diversity gate.
- Bias recovery: the first three unknowns are b_x, b_y, b_z; the
  fourth unknown must equal |b|^2 and is reported as the consistency
  check. The fit quality is the max residual
  max_k |(A x)_k - y_k| in nT^2.
- Calibration: subtracting the recovered bias from every sample,
  m_k - b, recovers the true field vectors h_k that the attitude
  consumers expect.
- ECSS-E-ST-60 frames attitude determination for European missions
  and is referenced, not reproduced (standards-map.yaml, ecss).

## Workflow

1. Collect the in-flight magnetometer samples m_k (body frame, nT)
   and the known field magnitude B_k at each sample (the IGRF
   magnitude at the spacecraft position, in nT). Mismatched lists,
   fewer than 4 samples, non-positive magnitudes, and non-3-vector
   samples are rejected with ValueError here.
2. Build the scalar-checking linear system with
   scalar_checking_design: row k is [-2*m_kx, -2*m_ky, -2*m_kz, 1]
   and the right side is y_k = B_k^2 - |m_k|^2.
3. Solve the batch least squares normal equations with
   least_squares_solve: A^T A x = A^T y by plain matrix multiply,
   solved by the partial-pivot Gaussian elimination of
   solve_linear_system. A pivot below the tolerance raises
   "insufficient attitude diversity" when the samples are confined to
   one line or one plane and cannot constrain all four unknowns.
4. Read the estimate dict from estimate_bias: the bias vector (the
   first three unknowns), bias_norm_nt (the recovered |b|),
   expected_sq_norm (the fourth unknown), and max_residual (the fit
   quality in nT^2).
5. Run the consistency check: the fourth unknown must equal the
   recovered |b|^2 and the max residual must be small before
   calibrated vectors can feed attitude determination.
6. Clean the raw samples with calibrate_measurement, subtracting the
   bias elementwise to recover the true field vectors for the
   attitude consumers.

## Worked example

Known bias b_true = (200, -150, 300) nT over ten deterministic unit
directions (the three axes, four body diagonals, (1, 0, 1)/sqrt(2),
(0.6, 0.8, 0), and the antipodal (-1, 0, -1)/sqrt(2)) with field
magnitudes B_k = 30000 + 1500*k nT for k = 0..9 (30000 to 43500 nT),
true fields h_k = B_k * u_k, noise-free synthetic samples
m_k = h_k + b_true (scripts/magnetometer_calibration_logic.py real
outputs):

- Recovered bias: 200.000000, -150.000000, 300.000000 nT; bias error
  2.322e-12 nT (identity bound 1e-6 nT).
- Recovered |b| = 390.512484 nT; true |b| = 390.512484 nT.
- Fourth unknown x[3] = 152500.000000 nT^2; |b_true|^2 = 152500 nT^2;
  consistency gap 9.622e-8 nT^2.
- Max residual max_k |(A x - y)_k| = 5.178e-7 nT^2.
- calibrate_measurement on sample 4 (the first body diagonal at 34500
  nT): (19918.584287, 19918.584287, 19918.584287) nT, equal to the
  true field; max calibrate error over all 10 samples 3.638e-12 nT.
- Collinear fixture (all samples along one axis): ValueError
  "insufficient attitude diversity"; 3 samples: ValueError "fewer
  than 4 measurements cannot constrain 4 unknowns".

## Pitfalls

- Feeding samples with poor attitude diversity: measurements confined
  to one line or one plane leave the normal equations singular and
  the elimination raises ValueError, which is the point of the gate
  rather than a solver bug.
- Treating the fourth unknown as part of the bias: x[3] is |b|^2, a
  consistency check against the recovered bias norm, not a fourth
  bias component.
- Skipping the consistency gate: a large gap between the fourth
  unknown and the recovered |b|^2, or a large max residual, means the
  scalar-checking model does not fit (sensor noise, a changing
  field) and the cleaned vectors should not feed attitude
  determination.
- Forgetting the IGRF is an input: this leaf never predicts the
  field; B_k comes from the field model at the sample position and
  time, and the batch inherits any IGRF magnitude error.
- Expecting scale estimation: hard-iron bias only. Scale factors and
  cross-axis terms stay in the residual because a linear encoding of
  the diagonal scale unknowns would make the design nonlinear.

## Verification

Deterministic, offline checks (scripts/test_magnetometer_calibration.py):
worked-example anchors above within the spec bounds (bias within
1e-6 nT, fourth unknown within 1e-4, consistency gap and max residual
below 1e-3, cleaned samples within 1e-6 nT of the true fields);
rotation invariance of the bias estimate under a fixed rotation of
the fixture; the hand-computed design rows and right sides of step 2;
the partial-pivot solver on 2 by 2, 3 by 3, and 4 by 4 systems;
ValueError rejection of length mismatches, 3 samples, zero and
negative field magnitudes, collinear and planar fixtures
("insufficient attitude diversity"), and calibrate_measurement length
mismatches; and repeated-call determinism with the documented dict
keys.

## Related leaves

- space-systems/adcs/attitude-determination-triad
- space-systems/adcs/attitude-determination-quest
- space-systems/adcs/gyro-allan-variance
- space-systems/adcs/star-tracker
- space-systems/adcs/magnetorquer-control

## Behavior contract (gate 3)

The scalar-checking magnetometer calibration logic is exercised by
the gate 3 contract test:
scripts/test_magnetometer_calibration.py against
scripts/magnetometer_calibration_logic.py (stdlib unittest, offline).
Run:

python3 scripts/test_magnetometer_calibration.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-60 text is
  copyright ESA; scalar-checking in-flight magnetometer calibration
  (also called TWOSTEP-style magnitude calibration in the open ADCS
  literature) is common estimation knowledge, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
