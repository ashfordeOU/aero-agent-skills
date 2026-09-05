---
name: attitude-determination-triad
description: "Use when the task is attitude determination from two vector measurements such as a sun sensor and magnetometer pair, coarse attitude estimation for initial acquisition, or computing the attitude quaternion and rotation angle that gate the ADCS attitude reference before fine pointing. Determine the spacecraft attitude matrix from a pair of non-parallel vector observations with the TRIAD algorithm: normalize the measured body frame directions and the matching reference frame directions, build the orthonormal triads from the cross products, assemble the 3 by 3 attitude matrix from the triad outer products, and validate the estimate with the rotation angle, the orthogonality error, and the inter observation angle consistency. Trigger: triad algorithm, attitude determination, vector observation, reference vector, body frame, attitude matrix, coarse attitude, sun sensor, magnetometer."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [triad-algorithm, triad-attitude-determination, vector-observation, reference-vector, attitude-matrix, coarse-attitude, sun-sensor-magnetometer, orthonormal-triad]
  version: 0.1.0
  author: Aero Agent Skills
---

# TRIAD Attitude Determination (space-systems/adcs/attitude-determination-triad)

Use when the task is spacecraft attitude determination from a pair
of vector observations: building the body and reference triads,
estimating the 3 by 3 attitude matrix, and validating the estimate
before it becomes the ADCS attitude reference.

## Domain quick reference

- TRIAD inputs: two non-parallel unit directions b1 and b2 measured
  in the body frame (for example a sun sensor and a magnetometer
  pair) and the same two directions r1 and r2 known in the
  reference frame (the Sun direction and the Earth field direction
  from an ephemeris or a field model).
- Orthonormal triad per frame: t1 = v1, t2 = normalize(v1 x v2),
  t3 = t1 x t2. The construction fails only when the two vectors
  are parallel or one of them is zero.
- Attitude matrix: A = B * R^T, with B and R the 3 by 3 matrices
  whose columns are the body and reference triad vectors. The
  matrix maps reference vectors into the body frame:
  v_body = A * v_ref.
- Rotation angle of the estimate:
  theta = acos((trace(A) - 1) / 2), in degrees at the API
  boundary.
- Validation: the orthogonality error, the largest element of
  A * A^T - I, must be near zero, and the angle between the two
  body observations must match the angle between the two reference
  vectors within tolerance.
- TRIAD is a deterministic two-observation estimate; it does not
  least-squares more than two vectors. Wahba solvers such as QUEST
  or the q-method generalize it to many observations. ECSS-E-ST-60
  frames attitude determination for European missions.

## Workflow

1. Collect the two measured directions in the body frame and the
   two known directions in the reference frame.
2. Check that neither pair is parallel and that the inter
   observation angle agrees across the frames with
   vector_angle_deg.
3. Build the body and reference triads with orthonormal_triad.
4. Assemble the attitude matrix with triad_matrix.
5. Read the rotation angle with rotation_angle_deg and the
   equivalent quaternion with triad_quaternion.
6. Validate with orthogonality_error and gate the ADCS attitude
   reference on the verdict.

## Pitfalls

- Feeding parallel observations: the cross product collapses and
  the triad is undefined, so the logic raises ValueError.
- Swapping the frames: the body vectors are the measured sensor
  directions and the reference vectors are the same directions
  computed in the inertial or orbit frame; swapping them
  transposes the estimate.
- Skipping the consistency check: when the angle between the body
  observations disagrees with the reference angle (noisy or
  mis-identified directions), the TRIAD estimate is meaningless.
- Forgetting that the inputs are directions: the triad construction
  normalizes internally, but the estimate is only as good as the
  unit-vector assumption.
- Confusing TRIAD with star identification: the star tracker leaf
  matches centroids to a catalog; TRIAD turns a matched pair of
  directions into an attitude.

## Behavior contract (gate 3)

The TRIAD matrix, validation, and quaternion logic is exercised by
the gate 3 contract test:
scripts/test_attitude_determination_triad.py against
scripts/attitude_determination_triad_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_attitude_determination_triad.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-60 text is
  copyright ESA; the TRIAD method is common attitude-determination
  knowledge published in the open literature, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
