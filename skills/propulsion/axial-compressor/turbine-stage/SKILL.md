---
name: turbine-stage
description: "Use when you must analyze a single axial turbine stage: compute the specific work output, the stage loading, the flow coefficient, the degree of reaction, the total-to-total efficiency, and the blade row losses from the blade speed, the axial velocity, the absolute flow angles, and the relative flow angles. Produces the velocity-triangle performance parameters in SI units that gate the turbine stage design review in the FAR-33 engine context. Trigger: axial turbine stage, stage loading, degree of reaction, flow coefficient, blade row loss, total-to-total efficiency, specific work output, turbine rotor, turbine stator."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: axial-compressor
  tags: [axial-turbine-stage, velocity-triangle, stage-loading, flow-coefficient, degree-of-reaction, blade-row-loss, turbine-efficiency, specific-work, total-to-total-efficiency, axial-velocity, blade-speed]
  version: 0.1.0
  author: AeroSkills
---

# Axial Turbine Stage (propulsion/axial-compressor/turbine-stage)

Use when the task is single axial turbine stage velocity-triangle
analysis: specific work output, stage loading, flow coefficient,
degree of reaction, blade row losses, and total-to-total or
total-to-static efficiency from the blade speed, axial velocity, and
flow angles.

## Domain quick reference

- Dixon convention: flow angles measured from the axial direction,
  all angles in RADIANS. Absolute angle alpha, relative angle beta.
- tan(beta) = u/ca - tan(alpha) at the same axial station; beta1,
  beta2 are the relative angles at rotor inlet and outlet.
- Specific work output w = u*ca*(tan(alpha1) - tan(alpha2)) in J/kg.
  Positive for a work-extracting stage (alpha1 > alpha2).
- Flow coefficient phi = ca/u, dimensionless.
- Stage loading psi = w/u**2, dimensionless; turbine stages run near
  psi = 1 to 3, higher than compressor stages.
- Degree of reaction r = 1 - ca/(2*u)*(tan(alpha1) + tan(alpha2)),
  dimensionless; r = 0 is an impulse stage, r = 0.5 is a symmetric
  50% reaction stage with equal enthalpy drops across rotor and
  stator rows.
- Row losses: nozzle loss = zeta_n*c1**2/2 and rotor loss =
  zeta_r*w2**2/2 in J/kg, with c1 = ca/cos(alpha1) and
  w2 = ca/cos(beta2); zeta_n and zeta_r are the row enthalpy loss
  coefficients (air-standard defaults 0.05 each).
- Total-to-total efficiency eta_tt = w/(w + nozzle_loss + rotor_loss),
  total-to-static efficiency eta_ts = w/(w + nozzle_loss +
  rotor_loss + c3**2/2) with the exit absolute angle alpha3 (axial
  exit alpha3 = 0 loses the full ca**2/2).
- Units: u, ca in m/s; angles in rad; w and losses in J/kg; phi, psi,
  r, eta dimensionless.

## Workflow

1. Fix the design point: blade speed u, axial velocity ca.
2. Set the absolute flow angles alpha1, alpha2; derive beta1, beta2
   from tan(beta) = u/ca - tan(alpha).
3. Compute the work output with specific_work.
4. Compute the dimensionless loading with flow_coefficient and
   stage_loading.
5. Compute the degree of reaction with degree_of_reaction; check the
   impulse (r = 0) and 50% reaction (r = 0.5) design limits.
6. Budget the row losses with blade_row_loss and compute the
   efficiencies with total_to_total_efficiency and
   total_to_static_efficiency.
7. Assemble the full assessment with stage_properties and gate the
   turbine stage design review on it.

## Pitfalls

- Degrees instead of radians: entering 45 for alpha1 instead of
  pi/4 changes the tangent and the work by a large factor; convert
  first.
- Angles from the tangential direction: this convention flips the
  tan terms and the sign of the work; keep angles from axial.
- Confusing alpha with beta: alpha is the absolute flow angle, beta
  the relative one; passing beta into specific_work double-counts
  the blade speed.
- Sign of work: alpha1 < alpha2 adds work to the flow (compressor
  sense); a turbine stage must show alpha1 > alpha2 for output.
- Negative loss coefficients: zeta_n or zeta_r below zero raise
  ValueError; do not catch and continue, the efficiency is
  meaningless.
- Non-physical inputs: u <= 0 or ca <= 0 raise ValueError.

## Behavior contract (gate 3)

The velocity-triangle logic is exercised by the gate 3 contract test:
scripts/test_turbine_stage.py against
scripts/turbine_stage_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_turbine_stage.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain) and covers engine type certification, not stage
  analysis methods; the velocity-triangle relations are common
  turbomachinery methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
