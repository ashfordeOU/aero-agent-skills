---
name: quaternion-algebra
description: "Use when you must compute single-step quaternion algebra with the Python standard library: form the Hamilton quaternion product, take the conjugate, norm, and inverse, normalize to a unit quaternion, rotate a 3-vector by a quaternion with the stated conjugate rotation convention, build a quaternion from an axis and angle or from yaw-pitch-roll angles with the ZYX convention, convert between quaternion and direction cosine matrix, and interpolate between two unit quaternions with spherical linear interpolation. Produces the product quaternion, the rotated vector, the converted angles or matrix, and the slerp result at the requested parameter. Trigger: quaternion product, quaternion multiply, rotate vector by quaternion, euler to quaternion, quaternion to euler, direction cosine matrix, slerp, quaternion conjugate, unit quaternion, axis angle to quaternion."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [quaternion-algebra, quaternion-product, rotate-vector-by-quaternion, euler-to-quaternion, quaternion-to-euler, direction-cosine-matrix, slerp, spherical-linear-interpolation, quaternion-conjugate, unit-quaternion, axis-angle-to-quaternion]
  version: 0.1.0
  author: Aero Agent Skills
---

# Quaternion Algebra (cross-cutting/numerics/quaternion-algebra)

Use when the task is a single-step quaternion calculation for
attitude, navigation, or control code: multiplying two rotations
stored as quaternions, rotating a vector, converting between
representations, or interpolating between two orientations, with the
Python standard library only (no numpy). The leaf implements the pure
algebraic toolkit: Hamilton product, conjugate, norm, inverse, vector
rotation, axis-angle, Euler ZYX and direction cosine matrix (DCM)
conversions, and spherical linear interpolation (slerp). It pairs with
cross-cutting/numerics/matrix-operations for the dense matrix layer
and with the gnc-autonomy and space-systems leaves that consume
quaternions; this leaf never marches a rotation through time.

## Domain quick reference

Conventions stated once, used everywhere in the module:
representation q = (w, x, y, z) with w the scalar part; Hamilton
(aerospace) product; vector rotation with the conjugate on the right,
v_rot = q * (0, v) * conj(q), a right-handed rotation matching
DCM(q) * v; Euler ZYX meaning the active matrix
R = Rz(yaw) * Ry(pitch) * Rx(roll).

- Norm and unit: |q| = sqrt(w^2 + x^2 + y^2 + z^2);
  normalize_quaternion(q) scales to unit length and raises ValueError
  on the zero quaternion.
- Conjugate and inverse: q* = (w, -x, -y, -z);
  q^-1 = q* / |q|^2, so the inverse of a unit quaternion is its
  conjugate (quaternion_inverse).
- Hamilton product (component form): with q1 = (w1, v1) and
  q2 = (w2, v2), q1*q2 = (w1*w2 - v1.v2, w1*v2 + w2*v1 + v1 x v2).
  The product is not commutative: q1*q2 != q2*q1. Rotating a vector
  by q1*q2 applies q2 first, then q1.
- Vector rotation: rotate_vector_by_quaternion(q, v) normalizes q and
  returns the vector part of q * (0, v) * conj(q); the equivalent
  v + 2*w*(u x v) + 2*u x (u x v) form holds with q = (w, u).
- Axis-angle: q = (cos(theta/2), sin(theta/2) * axis_hat); a non-unit
  axis is normalized, the zero axis raises ValueError.
- Euler ZYX (yaw-pitch-roll): euler_to_quaternion(yaw, pitch, roll)
  uses the half-angle formulas w = cy*cp*cr + sy*sp*sr,
  x = cy*cp*sr - sy*sp*cr, y = cy*sp*cr + sy*cp*sr,
  z = sy*cp*cr - cy*sp*sr with cy = cos(yaw/2) and so on.
- Quaternion to Euler: quaternion_to_euler(q) returns
  (yaw, pitch, roll, gimbal_flag) with pitch = asin(-R20) in
  [-pi/2, pi/2], yaw = atan2(R10, R00), roll = atan2(R21, R22); at
  gimbal lock (pitch near +/-90 deg) yaw is set to 0.0, roll carries
  the remaining rotation, and gimbal_flag is True.
- Quaternion to DCM: quaternion_to_dcm(q) builds the standard 3x3
  matrix from the components; dcm_to_quaternion(dcm) inverts it by the
  largest-diagonal (Shepperd) method with the sign fix w >= 0.
  A DCM with |det - 1| > 1e-3 or R^T R away from identity raises
  ValueError.
- Slerp: q(t) = (q0*sin((1-t)*Omega) + q1*sin(t*Omega)) / sin(Omega),
  Omega = acos(|q0.q1|); q1 is negated when q0.q1 < 0 for the shortest
  path and near-zero sin(Omega) falls back to renormalized linear
  interpolation. t outside [0, 1] raises ValueError.

## Workflow

1. Fix the representation: read the quaternion as (w, x, y, z) with
   quaternion(w, x, y, z) or pass a 4-sequence; every function
   validates its inputs and raises ValueError on malformed data.
2. Check or impose unit norm with quaternion_norm and
   normalize_quaternion before treating the conjugate as the inverse.
3. Compose two rotations with quaternion_product(q1, q2); recall the
   order convention (q2 applies first). To invert a rotation use
   quaternion_conjugate on a unit quaternion or quaternion_inverse
   in general.
4. Rotate a vector with rotate_vector_by_quaternion(q, v); verify the
   result against DCM(q) * v when a matrix check is wanted.
5. Build the quaternion from an axis and angle with
   axis_angle_to_quaternion, or from yaw-pitch-roll angles with
   euler_to_quaternion (state the ZYX convention in the report).
6. Convert to Euler angles with quaternion_to_euler and note the
   gimbal_flag when pitch approaches +/-90 deg, or to a matrix with
   quaternion_to_dcm and back with dcm_to_quaternion.
7. Interpolate between two unit quaternions with quaternion_slerp at
   the requested t in [0, 1]; the module picks the shortest path and
   returns a unit quaternion.
8. Confirm the deterministic checks with the contract test
   scripts/test_quaternion_algebra.py.

## Worked example

Anchor rotations (module outputs):
q1 = 90 deg about z: axis_angle_to_quaternion((0, 0, 1), pi/2) =
(0.70711, 0.0, 0.0, 0.70711); q2 = 90 deg about x:
(0.70711, 0.70711, 0.0, 0.0).

- Product and composition: q1*q2 = (0.5, 0.5, 0.5, 0.5) while
  q2*q1 = (0.5, 0.5, -0.5, 0.5), so the product is not commutative.
  q2 alone leaves e_x fixed (90 deg about x rotates about e_x), and
  q1*q2 maps e_x to e_y: rotating (1, 0, 0) by q1*q2 gives
  (2.22e-16, 1.0, 0.0), the same as rotating by q2 then q1 step by
  step. Rotating (1, 0, 0) by the 90-deg-z quaternion alone gives
  (2.22e-16, 1.0, 0.0), i.e. (0, 1, 0) within 1e-9; rotating
  (0, 1, 0) by q2 (90 deg about x) gives (0, 0, 1) within 1e-9.
- Euler ZYX round trip: euler_to_quaternion(30, 20, 10 deg) =
  (0.95155, 0.03813, 0.18931, 0.23930); quaternion_to_euler returns
  (30, 20, 10 deg) within 1e-9 with gimbal_flag False. The DCM of this
  quaternion is [[0.81380, -0.44097, 0.37852], [0.46985, 0.88256,
  0.01803], [-0.34202, 0.16318, 0.92542]] and dcm_to_quaternion
  recovers the quaternion (sign-fixed, w >= 0) within 1e-9.
- Gimbal lock: euler_to_quaternion(0, 90 deg, 0) converts back with
  pitch = pi/2, yaw = 0.0, roll = 0.0 and gimbal_flag True; with yaw
  30 deg and roll 45 deg the flag is True and pitch stays pi/2 while
  roll carries the sum of the two lost angles.
- Slerp midpoint: slerp between the identity (1, 0, 0, 0) and the
  90-deg-z quaternion at t = 0.5 gives (0.92388, 0.0, 0.0, 0.38268),
  exactly the 45-deg-z quaternion, within 1e-9; the result has unit
  norm.
- General inverse: q = (1, 2, 3, 4) has |q| = 5.47723 and
  q^-1 = (0.03333, -0.06667, -0.1, -0.13333); q*q^-1 = (1, 0, 0, 0).

## Verification

- Confirm rotate_vector_by_quaternion(axis 90-deg-z, (1, 0, 0))
  returns (0, 1, 0) within 1e-9 and that the same vector comes from
  DCM * v with quaternion_to_dcm.
- Confirm quaternion_product(q1, q2) on the two 90-deg anchors gives
  (0.5, 0.5, 0.5, 0.5), that q1*q2 rotates e_x to e_y, and that
  q1*q2 != q2*q1.
- Confirm the Euler ZYX 30-20-10 deg round trip stays within 1e-9
  with gimbal_flag False, and that pitch +/-90 deg sets gimbal_flag
  True.
- Confirm slerp(identity, 90-deg-z, 0.5) equals the 45-deg-z
  quaternion within 1e-9 and that slerp outputs have unit norm.
- Confirm the DCM round trip quaternion -> matrix -> quaternion stays
  within 1e-9 up to the w >= 0 sign fix.
- Confirm ValueError rejection of the zero axis, non-finite entries,
  non-3-vectors, DCMs that are not orthogonal (det off by more than
  1e-3), slerp t outside [0, 1], and zero-norm normalize or inverse.
- Run the contract test offline: python3
  scripts/test_quaternion_algebra.py (60 tests, deterministic).

## Pitfalls

- The algebra leaf is single-step only. Composing a rotation through
  an interval of time, or feeding vector measurements into an
  estimator, belongs to the consuming leaves below, not here.
- Product order: quaternion_product(q1, q2) applies q2 first. Getting
  the order backwards silently reverses the composition, so state the
  order convention in every report.
- Euler conventions are not universal: the module uses ZYX
  yaw-pitch-roll with R = Rz * Ry * Rx and reports angles in radians.
  Compare against the stated convention before mixing with other code.
- At gimbal lock yaw is returned as 0.0: the flag must be read, the
  returned yaw is arbitrary.
- q and -q encode the same rotation; dcm_to_quaternion returns the
  w >= 0 representative, so comparing quaternions from DCMs should
  allow an overall sign.
- Stdlib-only contract: the logic module imports nothing outside the
  Python standard library; keep it that way.

## Related leaves

- cross-cutting/numerics/matrix-operations: dense linear algebra for
  the matrix layer around the DCM conversions.
- cross-cutting/numerics/interpolation: scalar and spline
  interpolation on 1-D data, the non-rotational counterpart of slerp.
- gnc-autonomy/space/attitude-dynamics: the consuming leaf that
  carries quaternions through time for attitude motion.
- space-systems/adcs/attitude-determination-triad: attitude from
  vector measurements, which consumes the quaternion of this leaf as
  its output representation.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_quaternion_algebra.py

The test covers the worked anchors (90-deg rotations about z and x,
product composition and non-commutativity, e_x to e_y mapping, the
Euler ZYX 30-20-10 deg round trip, gimbal-lock flags, the slerp
midpoint as the 45-deg-z quaternion, DCM round trips), norm and
normalize identities, conjugate and inverse identities including the
general q*q^-1 = 1 check, the axis-angle anchors and zero-axis
rejection, the Euler to ZYX-matrix agreement, the largest-diagonal
DCM extraction with the sign fix, and ValueError rejection of the
zero axis, non-finite inputs, non-3-vectors, non-orthogonal DCMs,
out-of-range slerp parameters, and zero-norm normalize and inverse.

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. Hamilton quaternion algebra, Euler
  angle conventions, the DCM conversion and slerp are generic
  textbook numerical methodology, not RTCA, SAE, or IAQG content;
  summary and formulas only.
- compliance: STANDARDS-REF, gated: false.
