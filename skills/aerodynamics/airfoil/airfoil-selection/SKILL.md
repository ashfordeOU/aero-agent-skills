---
name: airfoil-selection
description: "Use when you must select an airfoil section for a wing design: score candidate airfoils by lift-to-drag ratio at the design condition, filter them by minimum thickness, and choose the best qualified section from classic airfoil data. Produces the candidate scoring, the thickness filter verdict, and the selected airfoil identifier that feeds the wing layout. Trigger: airfoil selection, wing design, lift to drag ratio, thickness, naca airfoils, section selection."
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
  subdomain: airfoil
  tags: [airfoil-selection, wing-design, lift-to-drag-ratio, thickness, naca-airfoils, section-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Airfoil Section Selection (aerodynamics/airfoil/airfoil-selection)

Use when the task is airfoil section selection for a wing: scoring
candidates by lift-to-drag ratio, filtering by thickness, and
choosing the best qualified section.

## Domain quick reference

- Classic airfoil data (NACA Report 824 and successors) supplies
  lift and drag coefficients per section.
- The design condition defines the target lift coefficient and
  Reynolds number.
- Thickness constrains the section: structural depth and internal
  volume come from the thickness ratio.
- Selection maximizes lift-to-drag ratio among sections that meet
  the minimum thickness.

## Workflow

1. Collect candidate sections with cl, cd, and thickness at the
   design condition.
2. Score each with ld_ratio.
3. Filter with thickness_ok.
4. Select with select_airfoil.
5. Confirm the choice against the design lift condition.

## Pitfalls

- Choosing by cl alone instead of lift-to-drag ratio.
- Ignoring the thickness constraint until the structure is sized.
- Comparing candidates at different Reynolds numbers.

## Behavior contract (gate 3)

The scoring, filtering, and selection logic is exercised by the
gate 3 contract test: scripts/test_airfoil_selection.py against
scripts/airfoil_selection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_airfoil_selection.py

## Compliance

- NACA Report 824 is US government work (public domain); summary
  and physics values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
