---
name: inertia-estimation
description: "Use when you must estimate mass properties for vehicle design: compute moments of inertia from masses and radii of gyration, move inertia between axes with the parallel axis theorem, and check the gyration radius against the component dimension. Produces the inertia estimates, the parallel axis transfers, and the gyration sanity verdict that feed the loads analysis. Trigger: mass properties, moment of inertia, radius of gyration, parallel axis theorem, inertia estimation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: mass-properties
  tags: [mass-properties, moment-of-inertia, radius-of-gyration, parallel-axis-theorem, inertia-estimation]
  version: 0.1.0
  author: AeroSkills
---

# Mass Properties Inertia Estimation (vehicle-design/mass-properties/inertia-estimation)

Use when the task is mass properties estimation: moments of
inertia, parallel axis transfers, and gyration radius sanity for
the loads analysis.

## Domain quick reference

- Moment of inertia from the radius of gyration: I = m * k^2.
- The parallel axis theorem moves inertia between axes:
  I = I_cg + m * d^2.
- A gyration radius must lie inside the component dimension.
- Mass properties feed the loads and dynamics analyses in the
  FAR-25 / CS-25 context.

## Workflow

1. Collect component masses and radii of gyration.
2. Compute inertia with moi_gyration.
3. Transfer axes with parallel_axis.
4. Check the gyration radius with gyration_sane.
5. Feed the verified inertia set to the loads analysis.

## Pitfalls

- Using a gyration radius larger than the component.
- Forgetting the mass times distance-squared term.
- Mixing axes without the parallel axis theorem.

## Behavior contract (gate 3)

The inertia, transfer, and sanity logic is exercised by the gate 3
contract test: scripts/test_inertia_estimation.py against
scripts/inertia_estimation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_inertia_estimation.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  inertia math is common mechanics, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
