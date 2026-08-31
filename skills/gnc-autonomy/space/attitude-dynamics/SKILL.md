---
name: attitude-dynamics
description: "Model spacecraft attitude dynamics with the Euler rotational equations of motion: propagate quaternion kinematics from angular velocity, integrate the inertia tensor and applied torques into angular rates, and compute angular momentum, torque-free nutation, gravity-gradient torque, and momentum wheel effects. Use when the task is spacecraft attitude dynamics, rotational kinematics, or momentum management for ADCS analysis, simulation, or sizing. The stdlib logic is deterministic and offline: quaternion rate and Euler integration steps, body-cone nutation rates, gravity-gradient torque at a given orbital radius, and wheel angular momentum from spin rate. Trigger: quaternion, angular velocity, inertia tensor, nutation, gravity gradient, momentum wheel, euler equations."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: space
  tags: [attitude, dynamics, quaternion, euler, kinematics, rotational, angular, momentum, inertia, torque, nutation, gravity, gradient, wheel, adcs, spacecraft]
  version: 0.1.0
  author: AeroSkills
---

# Attitude Dynamics (gnc-autonomy/space/attitude-dynamics)

Use when the task is spacecraft attitude dynamics: rotational
equations of motion, quaternion kinematics, or momentum management.

## Domain quick reference

- Euler rotational equations of motion for a rigid spacecraft with
  inertia tensor I and body angular velocity omega:
  H = I omega, H_dot = torque - omega x H, omega_dot = inv(I) H_dot.
  Torque-free spin about a principal axis is steady; off-axis spin
  produces the gyroscopic coupling that drives nutation and tumbling.
- Quaternion kinematics: with a scalar-first unit quaternion
  q = [w, x, y, z], q_dot = 0.5 q (x) [0, omega]. An explicit Euler
  step followed by renormalization propagates attitude for small dt.
- Angular momentum H = I omega is conserved (in inertial space) in
  torque-free motion. The inertia tensor is symmetric positive
  definite and diagonal in principal axes; a uniform box of mass m
  and sides a, b, c has Ixx = m (b^2 + c^2) / 12, and cyclic.
- Torque-free motion of an axisymmetric body: the angular momentum
  vector is fixed in space, the symmetry axis precesses around it at
  constant nutation angle, and omega precesses about the symmetry
  axis in the body frame at (ia/it - 1) omega3 (positive oblate,
  negative prolate, zero for a sphere).
- Gravity-gradient torque: tau = (3 mu / r^3) (r_hat x I r_hat),
  where r is the spacecraft position relative to the Earth's center
  in body coordinates and mu = 3.986004418e14 m^3/s^2 for Earth.
  A principal axis aligned with nadir gives zero torque, the
  equilibrium used by gravity-gradient-stabilized spacecraft.
- Momentum wheels: a wheel of inertia J_w spinning at omega_w about
  a body axis carries h = J_w omega_w and exchanges momentum with
  the body, so the conserved total is H = I omega + h; this is how
  reaction wheels despin and reorient a spacecraft without
  propellant.

## Workflow

1. Build the inertia tensor: principal moments from mass properties,
   e.g. inertia_tensor_of_box for a uniform box.
2. Compute the angular momentum H = I omega with angular_momentum.
3. Propagate attitude with quaternion kinematics: quat_rate for the
   derivative and quat_integrate_step for a renormalized Euler step.
4. Integrate the Euler equations with euler_rates (angular
   acceleration from inertia, torque, and the gyroscopic term
   omega x H) and angular_velocity_step.
5. For torque-free motion, report the nutation angle between H and
   the symmetry axis and the body-cone rate.
6. Add the gravity-gradient torque at the orbit radius and the wheel
   momentum, then re-evaluate the total momentum budget.

## Pitfalls

- Mixing scalar-first and scalar-last quaternion conventions; this
  logic uses q = [w, x, y, z] and Hamilton products throughout.
- Forgetting renormalization after an Euler quaternion step: the
  quaternion drifts off the unit sphere and the rotation is invalid.
- Dropping the gyroscopic term omega x H in Euler's equations; it is
  what produces nutation and tumbling.
- Treating the inertia tensor as a scalar; H = I omega must use the
  full 3x3 matrix when off-diagonal terms are present.
- Sign errors in the gravity-gradient torque convention; verify
  against the zero-torque case of r_hat along a principal axis.
- Confusing wheel momentum with body momentum: the wheel exchanges
  momentum with the body, so the total H = I omega + h is conserved,
  not I omega alone.
- Feeding rpm where rad/s is expected; convert with rpm_to_rad_s.

## Behavior contract (gate 3)

The Euler equations, quaternion kinematics, inertia, nutation,
gravity-gradient, and wheel logic is exercised by the gate 3 contract
test: scripts/test_attitude_dynamics.py against
scripts/attitude_dynamics_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_attitude_dynamics.py

## Compliance

- ECSS (European Cooperation for Space Standardization) standards are
  freely downloadable, copyright ESA; cite the source and paraphrase.
  This leaf cites ECSS as reference only per standards-map.yaml; the
  logic here is generic rigid-body dynamics, not ECSS text.
- compliance: STANDARDS-REF, gated: false.
