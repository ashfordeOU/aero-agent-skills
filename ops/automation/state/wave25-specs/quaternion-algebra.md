# Wave-25 leaf spec: quaternion-algebra (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/quaternion-algebra/
- Pack: numerics (existing siblings: matrix-operations,
  eigenvalue-decomposition, interpolation, least-squares-regression,
  fast-fourier-transform, etc.)
- Standards ids: naca-tr-824 (existing numerics convention; reference-only)
  (Ledger Standard: naca-tr-824)
- Family: cross-cutting

## Claim

Provide the standard quaternion algebra used across aerospace attitude,
navigation, and control code: construct a quaternion from an axis and
angle or from Euler angles with a stated convention, compute the
quaternion product, conjugate, norm, and inverse, rotate a 3-vector by a
quaternion (and recover the equivalent rotation matrix), convert between
quaternion and Euler angles and between quaternion and direction cosine
matrix, interpolate between two unit quaternions with spherical linear
interpolation (slerp), and check unit-norm and singular-convention edge
cases. Produces the transformed quaternion, rotated vector, converted
angles or matrix, and the slerp result with the interpolation parameter.

Does NOT do: attitude kinematics propagation over time (gnc-autonomy
space/attitude-dynamics owns quaternion rate and Euler integration),
attitude estimation from vector measurements (space-systems adcs
attitude-determination-triad owns TRIAD), attitude observers (gnc
estimation-filtering complementary-filter owns Mahony), quaternion
error feedback control laws (space-systems adcs reaction-wheel-control).
This leaf is the pure algebraic toolkit (single-step ops only).

## Model (implement exactly)

- Representation: quaternion q = (w, x, y, z), w the scalar part.
- Norm: |q| = sqrt(w^2+x^2+y^2+z^2). Normalize to unit when needed.
- Conjugate: q* = (w, -x, -y, -z).
- Inverse of unit quaternion = conjugate; general inverse q^-1 = q*/|q|^2.
- Product (Hamilton, aerospace convention): given q1=(w1,v1), q2=(w2,v2),
  q1*q2 = (w1*w2 - v1.v2, w1*v2 + w2*v1 + v1 x v2). Implement the
  explicit component form and assert the no-commutativity behavior.
- Rotate vector v by unit quaternion q: v_rot = q * (0, v) * q^-1 (or the
  equivalent v + 2*w*(v x u) + 2*u x (u x v) form); use the conjugate
  rotation convention consistently (state it).
- Axis-angle to quaternion: q = (cos(theta/2), sin(theta/2)*axis),
  ValueError on zero norm axis.
- Euler to quaternion: use the aerospace ZYX (yaw-pitch-roll) convention
  with the standard half-angle formulas; state the convention.
  Quaternion to Euler: inverse mapping with the atan2 branch and the
  gimbal-lock (pitch = +/-90 deg) handling returning a flag.
- Quaternion to DCM: the standard 3x3 matrix from the quaternion
  components; DCM to quaternion by the largest-diagonal method with the
  sign convention fix.
- Slerp: q(t) = (q0*sin((1-t)*Omega) + q1*sin(t*Omega))/sin(Omega),
  with Omega = acos(|q0.q1|), handling q0.q1 < 0 by negating q1 (shortest
  path) and Omega near 0 by linear interpolation.
Functions:
- quaternion(w,x,y,z) validated dataclass or tuple + helpers
- quaternion_norm(q), normalize_quaternion(q)
- quaternion_conjugate(q), quaternion_inverse(q)
- quaternion_product(q1,q2)
- rotate_vector_by_quaternion(q, v)
- axis_angle_to_quaternion(axis, angle_rad)
- euler_to_quaternion(yaw, pitch, roll)  (ZYX)
- quaternion_to_euler(q) -> (yaw, pitch, roll, gimbal_flag)
- quaternion_to_dcm(q), dcm_to_quaternion(dcm)
- quaternion_slerp(q0, q1, t)
ValueError on: zero axis, non-finite inputs, non-3-vector, DCM not
orthogonal within tolerance (det ~ 1 within 1e-3), t outside [0,1]
(clamp with a note or raise - pick raise for out-of-range, allow 0/1).

## Worked example

- q1 = axis-angle of 90 deg about z -> (cos45, 0, 0, sin45); q2 = 90 deg
  about x -> (cos45, sin45, 0, 0). Product q1*q2 maps e_x to e_y then?
  compute numerically and assert the rotated vector results (e.g.
  rotate (1,0,0) by 90 deg about z gives (0,1,0) within 1e-9).
- Euler ZYX yaw 30 deg, pitch 20 deg, roll 10 deg -> quaternion and back
  round trip within 1e-9; gimbal pitch 90 deg flag True.
- Slerp midpoint between identity and 90-deg-z quaternion equals the
  45-deg-z quaternion within 1e-9.
- DCM round trip identity within 1e-9.
Keep at least 20 test methods.

## Corpus tasks (ids w25-quaternion-algebra-1/2)

Distinctive tokens: quaternion product, quaternion multiply, rotate
vector by quaternion, euler to quaternion, quaternion to euler,
direction cosine matrix, slerp, quaternion conjugate, unit quaternion,
axis angle to quaternion. Avoid: propagate, kinematics, integrate,
observer, mahony, error feedback, triad, attitude estimate (those route
to the gnc/space/adcs siblings).

1. "rotate the body frame vector by the unit quaternion and convert the
   result back through the direction cosine matrix to verify the
   rotation"
2. "convert the yaw pitch roll angles to the quaternion with the ZYX
   convention and slerp between two attitude quaternions at the midpoint"

## SKILL body notes

Pure algebra leaf; pair with matrix-operations and the gnc/space adcs
leaves that consume quaternions. State the Hamilton product and the ZYX
convention explicitly in the body. Worked example uses module outputs.
