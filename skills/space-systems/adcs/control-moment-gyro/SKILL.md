---
name: control-moment-gyro
description: "Use when you must size and analyze a control moment gyro (CMG) cluster for agile spacecraft attitude control: compute the torque from the rotor momentum and the gimbal rate with the CMG torque law, derive the gimbal rates for a commanded torque with the pseudoinverse steering law and its null-space term, judge the torque amplification of the gimbal against a wheel actuator at equal momentum, evaluate the singularity measure and verdict of the gimbal state, and size the cluster momentum envelope of the pyramid array for the slew with the gimbal rate saturation flag. Produces the gimbal rates, the achieved torque, the envelope coverage verdict, and the singularity verdict that gate CMG selection. Trigger: control moment gyro, CMG cluster, gimbal rate, gimbal axis, steering law, singularity measure, gimbal lock, momentum envelope, pyramid cluster, torque amplification."
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
  tags: [control-moment-gyro, cmg-cluster, gimbal-rate, gimbal-axis, steering-law, singularity-measure, gimbal-lock, momentum-envelope, pyramid-cluster, torque-amplification]
  version: 0.1.0
  author: AeroSkills
---

# Control Moment Gyro (space-systems/adcs/control-moment-gyro)

Use when the task is the control moment gyro (CMG) actuator cluster for
agile spacecraft attitude control: converting a rotor momentum vector
swept about a gimbal axis into torque, deriving the gimbal rates that
produce a commanded torque through the cluster steering law, watching
the cluster singularity measure so the gimbal state never lands in
gimbal lock, and sizing the cluster momentum envelope so the agile slew
fits inside it. This leaf implements the single-gimbal CMG cluster math
in pure Python, stdlib only. It pairs with space-systems/adcs/
reaction-wheel-control for the alternate actuator (a wheel exchanges
momentum with the bus, a CMG only redirects its fixed rotor momentum),
space-systems/adcs/attitude-control-sizing for actuator selection, and
gnc-autonomy/space/attitude-dynamics for the torque environment; this
leaf is the CMG actuator cluster math, not the wheel control law, not
the desaturation dipole, not the momentum wheel slew sizing.

Conventions: the rotor momentum vector h of one CMG is fixed in
magnitude (50 N m s for the module sizing) and rotates about the gimbal
axis g at the gimbal rate delta_dot. A pyramid array carries N units
(4 typical) whose gimbal axes sit at the skew angle beta above the base
plane; the cluster geometry returned by pyramid_geometry keeps the unit
momentum directions in the base plane at zero gimbal angle, radially at
azimuths 2*pi*(i-1)/N.

## Domain quick reference

- Single CMG torque: tau = -delta_dot * (g x h), so for perpendicular
  geometry the magnitude is |tau| = h * |delta_dot|. The sign
  convention follows the momentum exchange: the torque on the
  spacecraft opposes the momentum rate of change.
- Torque amplification: a reaction wheel at the same momentum h =
  I_w * omega_w delivers I_w * alpha_w; the CMG delivers h * delta_dot,
  so the amplification ratio is h * delta_dot / (I_w * alpha_w). A
  modest rotor at high gimbal rate out-torques a wheel that must spin
  up its whole rotor.
- Pyramid geometry: unit i at azimuth phi_i = 2*pi*(i-1)/N has gimbal
  axis g_i = cos(beta) * t_i + sin(beta) * z (tangent direction t_i
  tilted up by the skew angle beta) and momentum direction
  h_i(delta_i) = cos(delta_i) * h_dir_i + sin(delta_i) * (g_i x
  h_dir_i). The standard skew angle 53.13 deg has cos(beta) = 3/5 and
  sin(beta) = 4/5.
- Cluster momentum: h_cluster = sum of the per-unit full momentum
  vectors CMG_MOMENTUM_NMS * h_i(delta_i).
- Momentum envelope: the maximum cluster momentum magnitude over the
  gimbal angle grid (coarse full-space scan plus the fine 2D scan of
  the skew-symmetric plane (a, b, -a, -b) that preserves the 180
  degree cluster symmetry about the base normal). The grid maximum is a
  lower bound on the true envelope, adequate for the slew feasibility
  check that the design slew momentum sits below it with margin.
- Jacobian: tau = J * delta_dot with J the 3 x N matrix whose columns
  are -g_i x h_i (full momentum vectors, so the columns carry the 50
  N m s magnitude scale).
- Steering law: delta_dot = J^T (J J^T)^-1 tau, augmented with the
  null-space term null_gain * (I - J^T (J J^T)^-1 J) n0, where n0 is
  the standard alternating unit null vector of the symmetric cluster
  and null_gain = 0.05 rad/s. J annihilates the null term, so it adds
  internal gimbal motion without changing the output torque.
- Singularity measure: S = det(J J^T). The verdict bands are nominal
  (S above the 1e8 threshold), near singularity (between the 1e-3
  floor and the threshold) and singular (at or below the floor, where
  the pseudoinverse steering law has no solution). The margin reported
  by the summary is S over the threshold.
- Gimbal rate limits: cmg_cluster_summary clips the steering rates to
  +-max_gimbal_rate (2 rad/s default), reports the achieved torque
  J times the clipped rates, and flags saturation when any raw rate
  exceeded the limit.
- Units are SI throughout: N m, N m s, rad, rad/s, kg m^2.
- ECSS frames the spacecraft ADCS design context; the relations above
  are standard CMG engineering methodology, summary-only.

## Workflow

1. Fix the single unit: rotor momentum h (module constant 50 N m s),
   gimbal axis g and gimbal rate delta_dot, then get the torque with
   cmg_torque and the amplification ratio with torque_amplification
   against a wheel inertia and acceleration at equal momentum.
2. Build the cluster with pyramid_geometry(skew_angle, num_units); the
   default sizing uses PYRAMID_SKEW_RADIANS = atan(4/3) (53.13 deg)
   and 4 units.
3. Set the gimbal state and read the total momentum with
   cluster_momentum(gimbal_angles, geometry).
4. Size the cluster for the slew: momentum_envelope(geometry, grid)
   gives the envelope maximum; confirm the design slew momentum
   (module constant 100 N m s) lies below it.
5. For a commanded torque, form the Jacobian with jacobian and derive
   the gimbal rates with steering_law(gimbal_angles, tau_cmd,
   geometry); the null-space term is included by default.
6. Assess the state with singularity_measure and classify it with
   singularity_verdict against the threshold, or run the whole pass in
   one call with cmg_cluster_summary for the clipped rates, achieved
   torque, verdict, margin and saturation flag.
7. Confirm the deterministic checks with the contract test
   scripts/test_control_moment_gyro.py.

## Worked example

Single CMG with h = 50 N m s along z and gimbal axis along x at
delta_dot = 1 rad/s: cmg_torque returns (0, 50, 0) N m, magnitude
50 N m. A wheel of 0.5 kg m^2 spun to 100 rad/s holds the same 50
N m s momentum and delivers 1 N m at 2 rad/s^2, so the amplification
ratio is 50.

4-CMG pyramid at skew 53.13 deg, 50 N m s per unit, gimbal state
(0.4, 0.1, -0.3, 0.2) rad:

- Cluster momentum magnitude 30.59 N m s; singularity measure S =
  3.2903e10, verdict nominal with margin 329 at the 1e8 threshold.
- Steering law for a commanded 20 N m roll torque:
  delta_dot = (0.1239, 0.1471, 0.0248, -0.2900) rad/s; J times these
  rates reproduces (20.0, 0.0, 0.0) N m within 1e-9 (the null term
  changes the rates but not the achieved torque; a zero command leaves
  pure null motion of magnitude 0.0477 rad/s).
- Momentum envelope: the grid scan (12 samples per axis) returns
  180.0 N m s, above the 100 N m s design slew momentum; the uniform
  tilt state at delta = -pi/2 on all units holds exactly 120 N m s
  along the base normal.
- Singularity boundary: at delta = +pi/2 on all units the cluster
  momentum reaches the axial envelope extremum, S collapses to zero
  and steering_law raises ValueError (gimbal lock). At 0.02 rad short
  of that state S = 3.598e7, the verdict is near singularity with
  margin 0.36, and the 20 N m command still steers within the 2 rad/s
  limit.
- Rate saturation: with max_gimbal_rate = 0.1 rad/s the summary clips
  the rates, sets the saturated flag, and the achieved torque drops to
  magnitude 10.8 N m, short of the 20 N m command.

## Verification

- Confirm cmg_torque with h = 50 N m s at 1 rad/s returns 50 N m and
  obeys tau = -delta_dot * (g x h) for oblique geometry.
- Confirm torque_amplification(50, 1, 0.5, 2) returns 50.
- Confirm the steering law at the worked gimbal state reproduces the
  stated rates and that J times the rates equals the commanded
  (20, 0, 0) N m within 1e-9 with and without the null term.
- Confirm S = det(J J^T) at the worked state equals 3.2903e10, the
  uniform tilt state is singular (steering raises ValueError), and the
  0.02 rad offset state is rated near singularity.
- Confirm the momentum envelope (grid 12) is at least 180 N m s, above
  both the 120 N m s uniform tilt state and the 100 N m s design slew
  momentum, and never above the 200 N m s absolute bound of four 50
  N m s units.
- Confirm the summary clips rates at the limit with the saturated
  flag and reports the achieved torque of the clipped rates.
- Confirm ValueError rejection of zero momentum, a gimbal rate over an
  explicit limit, non-finite inputs everywhere, num_units below 3,
  skew outside (0, pi/2), mismatched angle counts and non-positive
  limits.
- Run the contract test offline: python3
  scripts/test_control_moment_gyro.py (27 tests, deterministic).

## Related leaves

- space-systems/adcs/reaction-wheel-control: the alternate actuator,
  whose wheel torque law and desaturation dipole this leaf does not
  claim.
- space-systems/adcs/attitude-control-sizing: momentum wheel actuator
  sizing and margins for the maneuver, the selection context around
  this leaf.
- space-systems/adcs/magnetorquer-control: the low authority external
  torque complement for momentum management.
- gnc-autonomy/space/attitude-dynamics: the rigid body plant and
  torque environment that this leaf keeps simplified.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_control_moment_gyro.py

The test covers the worked example (single CMG 50 N m torque, the
steering rates for the 20 N m roll command with the achieved torque to
1e-9, the momentum envelope against the 100 N m s design slew
momentum), the pyramid geometry conventions (unit and orthogonal
gimbal and momentum directions, elevation sin(beta) = 4/5, radial
cancellation), the cluster momentum states (zero state, uniform tilt
120 N m s and its mirror), the Jacobian finite difference identity,
the singularity measure against a hand-computed det(J J^T) and its
nominal, near and singular states, the verdict bands, the pseudoinverse
steering with the annihilated null-space term and zero-command null
motion, the three-unit cluster, the clipped summary with the
saturation flag, and ValueError rejection of every non-physical input
class.

## Compliance

- Standards referenced, not reproduced: ECSS covers spacecraft ADCS
  design practice (standards-map.yaml); the CMG relations above are
  standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
