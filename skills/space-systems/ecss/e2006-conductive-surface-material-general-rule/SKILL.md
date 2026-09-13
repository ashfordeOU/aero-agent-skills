---
name: e2006-conductive-surface-material-general-rule
description: "Use when verify that an outer spacecraft material conducts well enough to hold its surface potential under the permitted ceiling per ECSS-E-ST-20-06C clause 6.3.3.2: convert bulk-resistivity and coating-thickness into sheet-resistance, compute the through-thickness ohmic-drop and the lateral potential-rise driven by the worst-case charging-current-density, select the governing drain-path, compare the resulting surface-potential against the ceiling, derive the maximum-allowable-resistivity, and grade the charge-decay-time-constant against the bleed-off limit. Trigger: ecss, e-st-20-06c, conductive-surface-material, surface-resistivity-limit, sheet-resistance, surface-potential-ceiling, charge-decay-time-constant, through-thickness-ohmic-drop, outer-surface-material-control."
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
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e2006-conductive-surface-material-general-rule, e-st-20-06c, conductive-surface-material, surface-resistivity-limit, sheet-resistance, surface-potential-ceiling, charge-decay-time-constant, outer-surface-material-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Conductive Outer-Surface Material General Rule (space-systems/ecss/e2006-conductive-surface-material-general-rule)

Use when the task is the general material rule of ECSS-E-ST-20-06C
clause 6.3.3.2: an exposed outer material has to bleed the charge it
collects away fast enough and completely enough that the potential it
settles at stays under the permitted ceiling, instead of floating up to
a value that can start a discharge.

## Domain quick reference

- The rule is a conduction requirement expressed as a potential limit.
  The material property that matters is bulk resistivity, but the
  quantity the requirement is written against is the potential the
  surface reaches, so the assessment always runs resistivity ->
  potential, never resistivity alone. A material that looks highly
  resistive can still pass in a thin layer, and a modest resistivity
  can fail over a long drain path.
- An exposed layer has two possible drain paths and they behave in
  opposite ways with thickness. Through the thickness to a grounded
  backing the ohmic drop is the collected current density times the
  bulk resistivity times the thickness, so a thinner layer is better.
  Laterally to a grounded edge the drop is set by the sheet resistance
  (resistivity divided by thickness) and the square of the distance to
  that edge, so a thinner layer is worse. Which path a surface really
  has is a design fact that has to be stated, not guessed.
- Where both paths exist, charge leaves by whichever one is easier, so
  the lower of the two computed potentials governs. Taking the higher
  one is not conservatism, it is the wrong model, and it condemns
  designs that are in fact compliant.
- Sheet resistance (ohm per square) is resistivity divided by
  thickness. It is the natural parameter for a coating measured on the
  bench and the one that makes the lateral term computable.
- Charge has to leave in time as well as in amplitude. The dielectric
  relaxation time of the material, resistivity times permittivity of
  free space times relative permittivity, is the decay constant; a
  layer whose decay constant is long compared with the charging
  timescale accumulates charge between events even when its steady
  potential looks acceptable.
- The conduction regime buckets (metallic conductor, static
  dissipative, partially dissipative, insulating dielectric) are a
  reporting aid derived from bulk resistivity. They do not replace the
  potential computation; they tell a reviewer at a glance why a
  surface passed or failed.

## Workflow

1. Normalize each outer-surface material record: identifier, material
   name, bulk resistivity, thickness, relative permittivity, distance
   to the nearest grounded edge, declared drain path and bonding
   state. Reject a non-positive resistivity or thickness, a relative
   permittivity below unity, and an unrecognized drain path.
2. Convert resistivity and thickness into sheet resistance.
3. Compute the through-thickness ohmic drop and the lateral potential
   rise for the worst-case charging current density of the mission
   environment. Keep both numbers in the record even though only one
   governs — the reviewer needs to see the path that was not taken.
4. Select the governing path from the declared drain path, taking the
   lower potential when both paths exist, and record which one won.
5. Compare the governing potential with the permitted ceiling, and
   derive the maximum allowable bulk resistivity that would satisfy
   the ceiling at this thickness and current density; that number is
   the procurement limit to write into the material specification.
6. Compute the charge-decay time constant and compare it with the
   bleed-off limit.
7. Emit findings — potential above the ceiling, decay time above the
   limit, material not bonded to structure — and aggregate the
   inventory. A material is compliant only when all three are clear.

## Pitfalls

- Grading a material on resistivity alone against a remembered
  threshold. The requirement is on the potential reached; thickness,
  drain geometry and the assumed current density all move the verdict.
- Applying the through-thickness formula to a surface whose only drain
  is a grounded edge at the rim. The two paths scale with thickness in
  opposite directions, so the wrong formula fails safe in one
  direction and dangerously in the other.
- Taking the maximum of the two computed potentials when both drains
  exist. Parallel paths mean the charge uses the easier one, so the
  minimum governs.
- Passing a surface whose steady potential is acceptable while its
  decay constant runs to hours. Between charging events the layer
  never returns to its rest state, and the differential offset against
  its neighbours grows.
- Treating a compliant potential as sufficient for an unbonded outer
  material. Without a bond to structure there is no reference for the
  computed drop, and the number is meaningless.
- Comparing a computed potential against its ceiling with a bare
  greater-than on raw floats. A product of powers can land a few units
  in the last place above a limit it is physically equal to; the logic
  absorbs that representation error at the comparison rather than
  moving the engineering limit.

## Behavior contract (gate 3)

The sheet-resistance conversion, both drain-path potentials, the
governing-path selection, the allowable-resistivity derivation, the
decay-time check and the inventory aggregation are exercised by the
gate 3 contract test:
scripts/test_e2006_conductive_surface_material_general_rule.py against
scripts/e2006_conductive_surface_material_general_rule_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_conductive_surface_material_general_rule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
