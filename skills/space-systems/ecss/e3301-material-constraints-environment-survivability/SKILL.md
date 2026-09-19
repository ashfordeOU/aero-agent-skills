---
name: e3301-material-constraints-environment-survivability
description: "Audit a mechanism material against the constraints of ECSS-E-ST-33-01C clauses 4.5.2.2 to 4.5.2.10. Use when a selected material still has to survive where it sits and harm nothing around it: refusing a fungus-nutrient left untreated through humid ground storage, grading limiting oxygen index against the atmosphere it will burn in, ruling out unstable materials and containing toxic ones, holding a surface in an optical path to its reflectance limit, comparing a degradation threshold with the dose times its design margin, computing atomic-oxygen recession from erosion yield and fluence, and checking every wetted pair. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-fungus-resistance, mechanism-flammability-oxygen-index, mechanism-toxic-offgassing-containment, mechanism-stray-light-reflectance, mechanism-radiation-degradation-threshold, atomic-oxygen-recession-depth, mechanism-fluid-compatibility."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-material-constraints-environment-survivability, mechanism-fungus-resistance, mechanism-flammability-oxygen-index, mechanism-toxic-offgassing-containment, mechanism-stray-light-reflectance, mechanism-radiation-degradation-threshold, atomic-oxygen-recession-depth, mechanism-fluid-compatibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Material Constraints and Environment Survivability (space-systems/ecss/e3301-material-constraints-environment-survivability)

Use when the task is the constraint set of ECSS-E-ST-33-01C clauses
4.5.2.2 to 4.5.2.10 -- taking a material that has already passed
selection and checking it against the seven ways a mechanism material
is still ruled out.

## Domain quick reference

- Seven constraints are carried, and they fail in different ways:
  fungus growth, flammability, toxic or unstable chemistry, stray
  light, radiation degradation, atomic-oxygen erosion and fluid
  compatibility. They are graded separately because a material can be
  perfect on six and excluded by the seventh.
- Fungus is a ground problem with a flight consequence. A nutrient
  material only matters where humid storage is declared, and there it
  is out unless it is treated -- growth bridges contacts and holds
  moisture against surfaces long after the humidity is gone.
- Flammability is a margin, not a property. What matters is how far
  the limiting oxygen index stands above the oxygen concentration the
  material will sit in, so the same material passes in air and fails in
  an enriched or pressurised volume.
- An unstable material is out everywhere. A toxic one is a question of
  where it sits: outside a habitable volume it is recorded, inside one
  it needs sealed containment rather than a vented enclosure.
- Stray light only applies inside an optical path, and inside one it
  is a performance limit with a number attached rather than a
  housekeeping preference.
- Radiation is graded on the threshold against the dose multiplied by
  its design margin. A threshold that clears the raw mission dose and
  not the margined one has no margin, which is the case the ratio is
  there to expose.
- Atomic-oxygen recession is erosion yield times fluence and nothing
  else. It is a two-factor multiplication that is easy to compute and
  easy to leave out, and where it exceeds the budget the answer is a
  protective coating, recorded as such rather than waved through.
- Fluid compatibility is checked per wetted pair. A material is
  compatible with the fluid it touches, not with the fluid the
  subsystem is named after.

## Workflow

1. Take the material with its environment: humid storage, the oxygen
   concentration and habitability of the volume it sits in, whether it
   is in an optical path, its mission dose, its atomic-oxygen fluence,
   and the fluids that wet it.
2. Grade fungus first, because it is the one constraint that turns on
   a ground-phase fact rather than a flight environment.
3. Take the flammability margin in percentage points and grade it
   against the required margin, accepting a case exactly on the
   requirement.
4. Rule on the unstable and toxic prohibitions, recording the
   containment level a toxic material is actually carried behind.
5. Grade stray light only where the surface is in the path, radiation
   on the capability ratio with the design margin folded in, and
   atomic-oxygen recession from erosion yield and fluence against the
   allowable thickness loss.
6. Check every wetted fluid against the incompatible list, then roll
   the seven results into one verdict that names the constraints
   actually violated rather than a single pass or fail.

## Pitfalls

- Grading flammability on the oxygen index alone. An index of
  twenty-eight is comfortable in air and unacceptable in an enriched
  atmosphere; without the ambient concentration the number decides
  nothing.
- Accepting a vented enclosure as containment for a toxic material in
  a habitable volume. Vented means the offgas reaches the crew more
  slowly, not that it does not reach them.
- Skipping the atomic-oxygen check because the mechanism is inside.
  The check applies to the exposed surfaces, and a deployable that
  spends the mission stowed still has a hinge liner facing ram
  direction when it is out.
- Grading radiation against the bare mission dose. The threshold has
  to clear the dose times its design margin, and a material that clears
  only the raw dose is being flown with no allowance for the dose
  estimate itself being wrong.
- Reading a fluid compatibility list at subsystem level. The wetted
  material sees the fluid in its own line, including the flush and
  proof media, and a seal qualified for the propellant can be attacked
  by the cleaning agent.
- Rolling seven constraints into one pass or fail. The repair for a
  reflectance overage is a coating and the repair for an unstable
  chemistry is a different material, so a verdict that does not name
  the constraint cannot be actioned.

## Behavior contract (gate 3)

Fungus grading, the oxygen-index margin, the unstable and toxic
prohibitions, stray-light reflectance, the radiation capability ratio,
atomic-oxygen recession with and without a coating, wetted-fluid
clashes and the roll-up verdict are exercised by the gate 3 contract
test:
scripts/test_e3301_material_constraints_environment_survivability.py
against
scripts/e3301_material_constraints_environment_survivability_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_material_constraints_environment_survivability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
