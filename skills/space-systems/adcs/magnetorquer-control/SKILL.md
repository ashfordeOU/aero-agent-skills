---
name: magnetorquer-control
description: "Compute the magnetic dipole moment for spacecraft magnetic attitude control with magnetorquers: solve torque = m x B for the required dipole from a torque demand and the local magnetic field vector, apply the B-dot detumbling law to damp body rates, check the achievable torque against the magnetorquer torque authority limit, warn when the torque demand lies along the field, and size the torque rod coils. Use when the task is magnetorquer control, dipole moment calculation, B-dot detumbling, cross-product torque steering, detumbling rate damping, or torque authority limits. Produces the dipole moment vector, the B-dot control dipole, the achievable torque magnitude, the underdetermined-axis warning, the coil sizing, and the orbit-averaged torque authority. Trigger: magnetorquer, dipole moment, B-dot, detumbling, torque authority, cross-product, magnetic field, coil sizing."
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
  tags: [adcs, magnetorquer, magnetic, dipole, moment, torque, detumbling, b-dot, cross-product, spacecraft, coil, field, torque-authority, b-field]
  version: 0.1.0
  author: Aero Agent Skills
---

# Magnetorquer Control (space-systems/adcs/magnetorquer-control)

Use when the task is spacecraft magnetic attitude control: computing
the magnetic dipole moment that produces a commanded torque through
the cross-product torque = m x B, B-dot detumbling of body rates,
torque authority limits, or torque rod coil sizing.

## Domain quick reference

- A magnetorquer (torque rod) is a coil that produces a magnetic
  dipole moment m (A m^2); the magnetic field B of the Earth exerts
  the control torque torque = m x B (N m) on the spacecraft.
- The torque is always perpendicular to B: m x B is orthogonal to B,
  so a magnetorquer can only produce torque about axes perpendicular
  to the local field. The torque component along B is unachievable,
  which is the underdetermined-axis limit of magnetic control.
- Required dipole: the minimal dipole that produces a torque demand
  perpendicular to B is m = (B x torque) / |B|^2. The component of
  the demand along B is returned as an underdetermined-axis warning.
- Achievable torque magnitude: |m x B| = |m| |B| sin(theta) where
  theta is the angle between m and B; the maximum for a given dipole
  magnitude is |m| |B|, reached when m is perpendicular to B.
- Torque authority: the largest torque a magnetorquer of dipole
  limit m_max can exert in a field B is m_max * |B|. Authority is
  weakest near the magnetic poles and strongest near the equator.
- B-dot detumbling law: damp the body rate omega by commanding
  m = gain * (omega x B), which equals -gain * Bdot because the body
  frame field derivative is Bdot = -omega x B. The resulting torque
  opposes the rate component perpendicular to B and damps it.
- Orbit-averaged authority: over one orbit the mean of m_max * |B|
  over the sampled field vectors estimates the average torque
  capability available for momentum dumping and pointing.
- Coil sizing: the dipole of a torque rod is N * I * A, the product
  of the number of turns, the drive current, and the coil area.
  Required current for a dipole demand is m / (N * A).
- Units: dipole moment in A m^2, field in T, torque in N m, rate in
  rad/s, coil current in A, area in m^2.
- Magnetic attitude control follows ECSS-E-ST-60 ADCS practice.

## Workflow

1. Get the torque demand vector (from the attitude controller or the
   detumbling law) and the local magnetic field vector B in the body
   frame.
2. Compute the required dipole m = (B x torque) / |B|^2 and check the
   underdetermined-axis warning: torque along B is not producible.
3. For detumbling, compute the B-dot dipole m = gain * (omega x B)
   from the measured body rate and field.
4. Compare the demanded dipole and the resulting achievable torque
   magnitude |m x B| against the magnetorquer torque authority
   limit m_max * |B|; clip the dipole to m_max when it exceeds the
   limit.
5. Size the torque rods: current per coil I = m / (N * A) for the
   selected turns and area; verify the coil current is within the
   driver limit.
6. Estimate the orbit-averaged torque authority from the field
   samples along the orbit to confirm the capability budget.

## Pitfalls

- Demanding torque along B: m x B can never produce it; detect the
  underdetermined axis and report it instead of returning a
  meaningless dipole.
- Dividing by a zero field: |B| = 0 makes the dipole formula
  singular; raise instead of returning nan.
- Forgetting that |m x B| depends on the angle: a dipole parallel to
  B produces zero torque even at full authority.
- Using B-dot gain with the wrong sign: m = gain * (omega x B) must
  oppose the rate, otherwise the law spins the spacecraft up.
- Sizing coils without the driver current limit: the required
  current m / (N * A) must be within what the electronics can
  supply.
- Treating the orbit-averaged authority as instantaneous capability:
  the average hides the per-axis gaps where B is nearly parallel to
  the demand.

## Behavior contract (gate 3)

The dipole computation, B-dot law, authority, and coil sizing logic
is exercised by the gate 3 contract test:
scripts/test_magnetorquer_control.py against
scripts/magnetorquer_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_magnetorquer_control.py

## Compliance

- ECSS (European Cooperation for Space Standardization) standards are
  freely downloadable, copyright ESA; cite the source and paraphrase.
  This leaf cites ECSS as reference only per standards-map.yaml; the
  logic here is generic magnetic attitude control physics (torque =
  m x B, B-dot damping), not ECSS text.
- compliance: STANDARDS-REF, gated: false.
