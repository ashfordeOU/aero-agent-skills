---
name: axial-compressor-stage
description: "Use when you must analyze a single axial compressor stage: compute the specific work, the flow coefficient, the work coefficient, the degree of reaction, and the stage pressure ratio from the blade speed, the axial velocity, the absolute flow angles, and the relative flow angles. Produces the velocity-triangle performance parameters in SI units that gate the compressor stage assessment in the FAR-33 engine design context. Trigger: axial compressor, velocity triangle, degree of reaction, flow coefficient, work coefficient, blade speed, stage pressure ratio, rotor, stator."
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
  tags: [axial-compressor, velocity-triangle, degree-of-reaction, flow-coefficient, work-coefficient, blade-speed, axial-velocity, compressor-stage]
  version: 0.1.0
  author: AeroSkills
---

# Axial Compressor Stage (propulsion/axial-compressor/axial-compressor-stage)

Use when the task is single axial compressor stage velocity-triangle
analysis: specific work, flow coefficient, work coefficient, degree of
reaction, and stage pressure ratio from the blade speed, axial
velocity, and flow angles.

## Domain quick reference

- Dixon convention: flow angles measured from the axial direction,
  all angles in RADIANS. Absolute angle alpha, relative angle beta.
- tan(beta) = u/ca - tan(alpha) at the same axial station; beta1,
  beta2 are the relative angles at rotor inlet and outlet.
- Specific work w = u*ca*(tan(alpha2) - tan(alpha1)) in J/kg.
  Positive for a compressing stage (alpha2 > alpha1).
- Flow coefficient phi = ca/u, dimensionless.
- Work coefficient psi = w/u**2, dimensionless.
- Degree of reaction r = ca/(2*u)*(tan(beta1) - tan(beta2)),
  dimensionless; 0.5 is a symmetric 50% reaction stage.
- Stage pressure ratio pi = (1 + eta*w/(cp*t01))**(gamma/(gamma-1)),
  dimensionless; t01 stagnation inlet temperature in K.
- Units: u, ca in m/s; angles in rad; w in J/kg; t01 in K; cp in
  J/(kg K); eta, phi, psi, r, pi dimensionless.
- Air-standard defaults: eta = 0.9, cp = 1005 J/(kg K), gamma = 1.4.

## Workflow

1. Fix the design point: blade speed u, axial velocity ca, stagnation
   inlet temperature t01.
2. Set the absolute flow angles alpha1, alpha2; derive beta1, beta2
   from tan(beta) = u/ca - tan(alpha).
3. Compute the specific work with specific_work.
4. Compute the dimensionless loading with flow_coefficient and
   work_coefficient.
5. Compute the degree of reaction with degree_of_reaction.
6. Compute the stage pressure ratio with stage_pressure_ratio.
7. Assemble the full assessment with stage_properties and gate the
   stage design review on it.

## Pitfalls

- Degrees instead of radians: entering 45 for alpha2 instead of
  pi/4 changes the tangent and the work by a large factor; convert
  first.
- Angles from the tangential direction: this convention flips the
  tan terms and the sign of the work; keep angles from axial.
- Confusing alpha with beta: alpha is the absolute flow angle, beta
  the relative one; passing beta into specific_work double-counts
  the blade speed.
- Non-physical inputs: u <= 0, ca <= 0, or t01 <= 0 raise ValueError;
  do not catch and continue, the numbers are meaningless.
- Sign of work: alpha2 < alpha1 extracts work (turbine sense); a
  pressure ratio below 1 means the stage is not compressing.

## Behavior contract (gate 3)

The velocity-triangle logic is exercised by the gate 3 contract test:
scripts/test_axial_compressor_stage.py against
scripts/axial_compressor_stage_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_axial_compressor_stage.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain) and covers engine type certification, not stage
  analysis methods; the velocity-triangle relations are common
  turbomachinery methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
