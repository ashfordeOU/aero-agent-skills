---
name: failure-criteria
description: "Use when you must evaluate a composite lamina against strength failure criteria: compute the Tsai-Wu, Tsai-Hill, and max-stress failure indices from the in-plane stresses and the ply allowables, and return the failure verdict. Produces each criterion index, the governing criterion, and the pass or fail verdict for the ply stress state. Trigger: lamina failure, tsai wu, tsai hill, max stress, failure index, composite ply strength, in plane stress."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [failure-criteria, tsai-wu, tsai-hill, max-stress, failure-index, lamina, ply-allowables, composite-lamina]
  version: 0.1.0
  author: Aero Agent Skills
---

# Lamina Failure Criteria (structures/composites/failure-criteria)

Use when the task is lamina failure assessment for a composite ply:
Tsai-Wu, Tsai-Hill, and max-stress failure indices under in-plane
stress.

## Domain quick reference

- A lamina has strength allowables in material axes: fiber tension
  Xt, fiber compression Xc, transverse tension Yt, transverse
  compression Yc, and in-plane shear S.
- A failure index compares the applied stress state with the
  allowables; an index at or above 1.0 means the ply fails that
  criterion.
- Max-stress checks each stress component independently against its
  own allowable, so it ignores interaction between components.
- Tsai-Hill couples the two normal stresses with an interaction
  term and uses the tensile allowables in its classic form.
- Tsai-Wu is a quadratic interaction criterion whose linear terms
  capture tension and compression asymmetry.
- Composite airframe certification under FAR-25 relies on
  statistically based ply allowables; these criteria evaluate the
  ply stress state against them.

## Workflow

1. Collect the lamina in-plane stresses s1, s2, t12 and the
   allowables Xt, Xc, Yt, Yc, S, all in MPa.
2. Compute the Tsai-Wu index with tsai_wu_index.
3. Compute the Tsai-Hill index with tsai_hill_index.
4. Compute the max-stress index with max_stress_index.
5. Combine the three with failure_verdict; the ply fails when any
   index is at or above 1.0.

## Pitfalls

- Mixing units: keep every stress and allowable in MPa (the Pa/MPa
  mix is the classic bug class here).
- Using the compression allowables in the classic Tsai-Hill form,
  which is written for tension.
- Reading an index of exactly 1.0 as pass; 1.0 is the failure
  boundary, so treat index >= 1.0 as failure.
- Forgetting that max-stress checks components independently while
  Tsai-Wu and Tsai-Hill include interaction terms.
- Missing the sign convention: s1 and s2 are signed, so max-stress
  must pick Xt or Xc (Yt or Yc) by the stress sign.

## Behavior contract (gate 3)

The Tsai-Wu, Tsai-Hill, max-stress, and verdict logic is exercised by
the gate 3 contract test: scripts/test_failure_criteria_logic.py
against scripts/failure_criteria_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_failure_criteria_logic.py

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25) is US
  government work (public domain); the failure criteria are common
  strength-of-materials knowledge, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
