---
name: laminate-stiffness
description: "Use when you must compute the stiffness of a composite laminate with classical lamination theory: build the ply stiffness from the material constants, rotate it to the ply angle, and assemble the A matrix for a symmetric laminate. Produces the ply stiffness, the rotated stiffness with coupling terms, and the laminate A matrix used in strength and stability analyses. Trigger: composite laminate, classical lamination theory, ply stiffness, laminate a matrix, symmetric laminate, composites."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [composite-laminate, classical-lamination-theory, ply-stiffness, laminate-a-matrix, symmetric-laminate, composites]
  version: 0.1.0
  author: Aero Agent Skills
---

# Composite Laminate Stiffness (structures/composites/laminate-stiffness)

Use when the task is composite laminate stiffness with classical
lamination theory: ply stiffness, rotation, and the symmetric
laminate A matrix.

## Domain quick reference

- A ply has orthotropic stiffness in material axes: Q11, Q12,
  Q22, Q66 from the engineering constants.
- Rotation to the laminate axes produces Q-bar; the coupling terms
  Q16 and Q26 vanish for 0 and 90 degree plies.
- The laminate A matrix sums Q-bar times ply thickness; for a
  balanced symmetric laminate the A16 and A26 terms vanish.
- Composite airframe practice sits in the FAR-25 / CS-25
  certification context for transport aeroplanes.

## Workflow

1. Collect ply engineering constants E1, E2, nu12, G12.
2. Build the material stiffness with ply_stiffness.
3. Rotate each ply with rotated_ply_stiffness.
4. Assemble the A matrix with laminate_a_matrix.
5. Confirm the coupling terms are small for symmetric balanced
   laminates.

## Pitfalls

- Forgetting nu21 = nu12 * E2 / E1 in the denominator.
- Assembling an unsymmetric stack and reading coupling terms as
  zero.
- Mixing degrees and radians in the rotation.

## Behavior contract (gate 3)

The ply, rotation, and A matrix logic is exercised by the gate 3
contract test: scripts/test_laminate_stiffness.py against
scripts/laminate_stiffness_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_laminate_stiffness.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the CLT
  math is common mechanics, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
