---
name: six-dof-simulation
description: "Use when you must simulate the rigid body motion of an aircraft with the six degree of freedom body axis equations of motion: compute the body axis accelerations from the applied aerodynamic forces and moments, compute the angular accelerations from the moments and the inertia tensor, form the state derivative of the state vector u v w p q r phi theta psi, and propagate the state one step with a fourth order Runge Kutta integrator to integrate the equations of motion over the simulation step. Produces the propagated state, the Euler angle rates from the body angular velocities p q r, and the attitude angles over the step. Trigger: six degree of freedom, body axis equations of motion, Runge Kutta, Euler angle rates, state vector, angular velocities."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: flight-dynamics-sim
  tags: [six-dof-simulation, body-axis, runge-kutta, euler-angles, rigid-body, equations-of-motion, state-vector, angular-velocities, rk4, attitude-kinematics]
  version: 0.1.0
  author: Aero Agent Skills
---

# Six-DOF Simulation (flight-mechanics/flight-dynamics-sim/six-dof-simulation)

Use when the task is rigid body aircraft simulation with the six
degree of freedom body axis equations of motion: force and moment
balance, Euler angle kinematics, and Runge Kutta propagation of the
state vector.

## Domain quick reference

Documented convention: body axes fixed in the aircraft, x forward,
y out the right wing, z down. The state vector is
[u, v, w, p, q, r, phi, theta, psi]: translational velocities
u, v, w in m/s, angular rates p, q, r in rad/s, and the Euler angles
phi (roll), theta (pitch), psi (yaw) in radians. The inputs are the
non-gravity body-axis loads: forces (X, Y, Z) in N, moments
(L, M, N) in N m, the mass m in kg, and the principal inertias
(Ixx, Iyy, Izz) in kg m^2 (products of inertia zero for a symmetric
aircraft). Weight enters through the gravity terms with g = 9.80665
m/s^2.

- Translational equations of motion (flat Earth, constant mass):
  u_dot = X/m - q w + r v - g sin(theta)
  v_dot = Y/m - r u + p w + g sin(phi) cos(theta)
  w_dot = Z/m - p v + q u + g cos(phi) cos(theta)
- Rotational equations (Euler rigid body equations about principal
  axes):
  p_dot = (L + (Iyy - Izz) q r) / Ixx
  q_dot = (M + (Izz - Ixx) r p) / Iyy
  r_dot = (N + (Ixx - Iyy) p q) / Izz
- Euler angle kinematics (body angular rates to attitude rates):
  phi_dot = p + tan(theta) (q sin(phi) + r cos(phi))
  theta_dot = q cos(phi) - r sin(phi)
  psi_dot = (q sin(phi) + r cos(phi)) / cos(theta)
- Fourth order Runge Kutta: one propagation step combines the
  derivative evaluations k1, k2, k3, k4 of the full nine-component
  state derivative and updates the state with the weighted average
  h (k1 + 2 k2 + 2 k3 + k4) / 6. The local error is fifth order in
  the step, so halving the step shrinks the error by about 32.
- Kinetic energy: 0.5 m (u^2 + v^2 + w^2) plus the rotational part
  0.5 (Ixx p^2 + Iyy q^2 + Izz r^2); used for the energy consistency
  check of a propagation step.

## Workflow

1. Collect the state vector (u, v, w, p, q, r, phi, theta, psi), the
   body-axis forces and moments, the mass, and the principal
   inertias.
2. Compute the Euler angle rates from p, q, r, phi, theta with
   euler_angle_rates.
3. Form the full nine-component state derivative with
   body_axis_derivative: the translational accelerations, the angular
   accelerations, and the attitude rates.
4. Propagate the state over the step with rk4_step and the fourth
   order Runge Kutta update.
5. Check the step with kinetic_energy when a work or energy budget is
   part of the simulation.

## Pitfalls

- Forgetting that the forces and moments are the non-gravity loads:
  weight is not an input force, it enters through the g terms, so a
  level trimmed aircraft needs Z = -m g, not Z = 0.
- Feeding degrees where radians are expected: phi, theta, psi and the
  rates are all radians and rad/s.
- Swapping the inertia roles in the gyroscopic terms: the p equation
  uses (Iyy - Izz), the q equation uses (Izz - Ixx), the r equation
  uses (Ixx - Iyy).
- Ignoring gimbal lock: psi_dot divides by cos(theta), so theta at
  plus or minus 90 degrees is singular and euler_angle_rates raises
  ValueError.
- Treating the Euler angle rates as the body angular rates: p, q, r
  are not phi_dot, theta_dot, psi_dot except at small angles.
- Using too large a step: RK4 is fourth order accurate, but a step
  that moves theta through the singularity still fails.

## Behavior contract (gate 3)

The six degree of freedom logic is exercised by the gate 3 contract
test: scripts/test_six_dof_simulation.py against
scripts/six_dof_simulation_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_six_dof_simulation.py

## Compliance

- ARP4754A (SAE) gives guidance for the development of aircraft
  systems, including simulation and verification of system behavior
  during development; this leaf cites it as reference only per
  standards-map.yaml. The equations here are generic rigid body
  dynamics, not ARP4754A text.
- compliance: STANDARDS-REF, gated: false.
