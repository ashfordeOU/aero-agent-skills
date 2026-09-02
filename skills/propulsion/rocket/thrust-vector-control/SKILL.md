---
name: thrust-vector-control
description: "Use when you must size or analyze a rocket thrust vector control (TVC) system: compute the side force from the engine thrust and the nozzle deflection angle, the control torque about the vehicle center of gravity from the side force and the moment arm, and the axial thrust loss from the deflection cosine, and size the actuator authority the gimbal actuators must deliver. Covers the TVC mechanisms: gimbaled engine or nozzle, flex-seal nozzle, jet vanes, and liquid injection, and contrasts thrust vector control with aerodynamic control surfaces for launch vehicles and upper stages. Produces the deflection angle, side force, control torque, axial thrust loss, and actuator sizing in consistent SI units. Trigger: thrust vector control, tvc, gimbal deflection, nozzle deflection, side force, control torque, axial thrust loss, actuator authority, jet vanes, flex-seal nozzle."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [thrust-vector-control, tvc, gimbal-deflection, nozzle-deflection, side-force, control-torque, axial-thrust-loss, actuator-authority, jet-vanes, flex-seal-nozzle, liquid-injection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Thrust Vector Control (propulsion/rocket/thrust-vector-control)

Use when the task is sizing or analyzing a rocket thrust vector control
system: deflection-driven side force, control torque about the center
of gravity, axial thrust loss, and the actuator authority the gimbal
actuators must deliver.

## Domain quick reference

- TVC mechanisms: a gimbaled engine or nozzle pivots the whole thrust
  chamber on a gimbal bearing; a flex-seal nozzle bends a flexible
  joint between the fixed and the movable nozzle sections (common on
  solid rocket motors); jet vanes are heat-resistant vanes in the
  exhaust stream; liquid injection injects a secondary fluid into the
  diverging section to deflect the flow with an oblique shock.
- The deflection angle delta is the angle between the deflected thrust
  vector and the vehicle axis.
- Side force: F_side = T * sin(delta), perpendicular to the vehicle
  axis.
- Control torque about the center of gravity: M = F_side * L, where L
  is the moment arm from the gimbal point to the center of gravity.
- Axial thrust loss from the deflection: T * (1 - cos(delta)); for
  small angles this is about T * delta^2 / 2.
- Actuator authority has three components: angular authority (max
  deflection), rate (deg/s, sets the achievable attitude bandwidth),
  and torque (overcomes bearing friction, hinge moments, and inertia).
- TVC produces control force only while the engine thrusts, but it
  works at zero dynamic pressure and in vacuum; aerodynamic control
  surfaces produce force from q * S * CN and lose authority as dynamic
  pressure falls, so upper stages rely on TVC alone.
- Practical deflection limits are roughly +/-5 to +/-15 deg; beyond
  that the cosine loss and actuator loads grow quickly.

## Workflow

1. Collect the engine thrust T, the gimbal deflection angle delta, and
   the moment arm L from the gimbal point to the center of gravity.
2. Compute the side force with side_force(thrust, deflection_rad).
3. Compute the control torque with control_torque(thrust,
   deflection_rad, moment_arm).
4. Compute the axial thrust loss with axial_thrust_loss(thrust,
   deflection_rad) and the retained fraction with axial_thrust_ratio.
5. Size the actuator: actuator_authority_required(required_torque,
   moment_arm) gives the side force the actuator must deliver, and
   deflection_angle_for_side_force gives the deflection needed for a
   demanded side force; compare it with the actuator angular authority
   to check saturation.

## Pitfalls

- Routing nozzle flow questions here: area ratio, exit Mach, choked
  mass flow, and ideal thrust belong to nozzle-design; TVC works with
  the already-designed thrust vector.
- Routing aerodynamic control questions here: hinge moments, control
  surface effectiveness, and aero control authority belong to the
  control-surface-effectiveness and control-surface-sizing leaves;
  TVC sizing is the thrust-driven analog.
- Routing delta-v and stage questions here: rocket equation, mass
  ratio, and staging belong to rocket-sizing and rocket-staging; TVC
  is attitude control, not trajectory energy.
- Using degrees in the trigonometry: the logic module takes radians;
  convert deg * pi / 180 before calling.
- Dropping the cosine loss at large deflection: a 15 deg deflection
  loses about 3.4% of the axial thrust, which matters for ascent
  performance budgets.
- Mixing up the moment arm: the arm is from the gimbal point to the
  center of gravity, not the nozzle length or the vehicle length.
- Assuming control without thrust: TVC produces no side force when the
  engine is off; coast phases need other attitude control.
- Treating rate and torque as interchangeable: a slow high-torque
  actuator cannot recover from a fast disturbance; both specs must
  close the loop with the control law.

## Behavior contract (gate 3)

The side force, control torque, axial thrust loss, deflection-for-
side-force, and actuator authority logic is exercised by the gate 3
contract test: scripts/test_thrust_vector_control.py against
scripts/thrust_vector_control_logic.py (stdlib unittest, offline).
Run:
python3 skills/propulsion/rocket/thrust-vector-control/scripts/test_thrust_vector_control.py

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA download
  (ecss.nl/standards); TVC force and torque geometry is standard
  mechanics, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
