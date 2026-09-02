---
name: cfd-turbulence-modeling
description: "Use when you must estimate the wall-normal first cell height for a CFD mesh: compute the y plus value from the friction velocity and kinematic viscosity, derive the friction velocity from the wall shear stress or the skin friction coefficient, and recommend the turbulence model and wall treatment for the boundary layer. Produces the y plus value, the friction velocity, and the turbulence model recommendation that size the near-wall mesh. Trigger: turbulence model, y plus, friction velocity, boundary layer, wall treatment, cfd."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: cfd
  tags: [cfd, turbulence-modeling, y-plus, friction-velocity, boundary-layer, wall-treatment]
  version: 0.1.0
  author: Aero Agent Skills
---

# CFD Turbulence Modeling (aerodynamics/cfd/cfd-turbulence-modeling)

Use when the task is CFD turbulence modeling for a wall-bounded
flow: sizing the first cell height with y plus, deriving the
friction velocity, and selecting the turbulence model and wall
treatment.

## Domain quick reference

- The dimensionless wall distance is y+ = y * u_tau / nu, with y
  in meters, u_tau in m/s, and nu in m^2/s; it measures how far
  the first cell center sits from the wall in wall units.
- The friction velocity u_tau = sqrt(tau_w / rho), with tau_w in
  Pa and rho in kg/m^3, scales the near-wall velocity profile.
- From the skin friction coefficient, u_tau = v_inf * sqrt(cf / 2),
  with v_inf in m/s.
- The target y+ drives the model choice: resolve the viscous
  sublayer at y+ about 1 (k-omega SST), blend at y+ about 30
  (realizable k-epsilon), or use wall functions up to y+ about
  300 (SA with wall functions).
- NACA Report 824 anchors classic airfoil boundary-layer data used
  to sanity-check skin friction and transition behavior.

## Workflow

1. Collect y, u_tau, and nu (or tau_w and rho, or cf and v_inf).
2. Compute the y plus value with y_plus.
3. Derive the friction velocity with friction_velocity or
   friction_velocity_from_cf.
4. Choose the turbulence model with
   turbulence_model_recommendation.
5. Size the first cell height from the target y+.

## Pitfalls

- Targeting y+ about 30 while running a low-Reynolds-number model
  that needs the sublayer resolved; the model and the y+ target
  must agree.
- Mixing units in u_tau: seconds for the friction velocity with
  centimeters for y gives a y plus off by orders of magnitude.
- Ignoring separation when choosing the model; wall functions
  degrade in separated regions, so flag separated flow even when
  the y+ band suggests a wall-function model.

## Behavior contract (gate 3)

The y plus, friction velocity, and recommendation logic is
exercised by the gate 3 contract test: scripts/test_cfd_turbulence.py
against scripts/cfd_turbulence_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_cfd_turbulence.py

## Compliance

- NACA Report 824 is US government work (public domain); summary
  and reference data only, per standards-map.yaml. Turbulence
  modeling guidance is common CFD methodology, not reproduced
  text.
- compliance: STANDARDS-REF, gated: false.
