---
name: q7021-manned-areas-interface
description: "Assess whether a material may be installed in a crewed compartment from its ECSS-Q-ST-70-21C flammability entry, applying the result to the habitable-volume material control of ECSS-Q-ST-70C. Use when a recorded rating must become a usage decision and the cabin atmosphere is not the atmosphere the specimen saw. Compares tested oxygen partial pressure against the cabin, treats a milder test as no evidence, checks installed thickness against the tested band, weighs exposed area and mass, and returns accepted, accepted-with-containment, needs-assessment or rejected. Trigger: ecss, q-st-70-21, crewed-compartment-material-control, habitable-volume-flammability, flammability-use-atmosphere-coverage, flammability-exposed-area-limit, flammability-containment-mitigation."
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
  tags: [ecss, q-st-70-21-flammability-scope, q7021-manned-areas-interface, crewed-compartment-material-control, habitable-volume-flammability, flammability-use-atmosphere-coverage, flammability-exposed-area-limit, flammability-containment-mitigation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Flammability — Crewed Compartment Interface (space-systems/ecss/q7021-manned-areas-interface)

Use when the task is the interface step that hands an ECSS-Q-ST-70-21C
flammability result to the material control of a habitable compartment
under ECSS-Q-ST-70C — turning a recorded rating into an installation
decision for a named location, and rolling those decisions up.

## Domain quick reference

- An entry is evidence only inside the atmosphere it was obtained in.
  The compartment's oxygen partial pressure is what the tested partial
  pressure has to bound. Thirty percent oxygen at 70 kPa is milder than
  sea-level air, so a result that looks enriched can still be no
  evidence at all for a normal cabin.
- An entry is evidence only for the configuration tested. An installed
  thickness outside the tested band is a different configuration and
  the entry does not speak for it; that is an assessment, not a pass.
- A propagating material is not automatically excluded from a crewed
  compartment. It is excluded from open installation. Sealed
  non-combustible containment keeps it away from cabin air; a quantity
  small enough that there is nothing to propagate through still needs a
  written assessment rather than a silent pass.
- A vented metal housing is not a seal. It stops dripping material
  reaching what is below; it does not stop a flame front reaching cabin
  air, and treating the two as one mitigation is the common error.
- A material that self-extinguishes but drips burning material is safe
  above nothing and unsafe above something ignitable. The geometry of
  the installation, not the rating alone, decides.
- A compartment is more than its worst item. Exposed area of everything
  only acceptable with containment, or still under assessment, is
  summed against a budget, because ten small exceptions make one large
  one and nobody reviews the tenth.

## Workflow

1. Validate the entry: a recorded rating from the known set, a tested
   oxygen partial pressure, a tested thickness.
2. Validate the usage: location, cabin oxygen fraction and total
   pressure, installed thickness, exposed area, mass, whether anything
   ignitable sits below, and the containment form.
3. Compute the compartment's oxygen partial pressure and compare it
   with the tested value; a milder test is a reason, not a pass.
4. Compare installed thickness with the tested band inside its
   tolerance.
5. With either check failed, the usage needs assessment and no rating
   shortcut applies.
6. Otherwise apply the rating: propagating goes to containment, to the
   quantity limit with an assessment, or to rejection; a drip
   restriction goes to the geometry below the item; a clean rating is
   accepted.
7. Sum exposed area across contained and unresolved items and compare
   it with the compartment budget.
8. Report every location with its disposition and reasons, the
   governing disposition, the exception area and the findings.

## Pitfalls

- Comparing oxygen percentages instead of partial pressures. It passes
  a reduced-pressure enriched test as evidence for sea-level air.
- Reading a pass at one thickness as a pass at every thickness. The
  tested band is part of the evidence.
- Treating a vented housing as a seal for a propagating material.
- Exempting a small propagating item silently. Small is a reason to
  assess, not a reason to skip the record.
- Judging the compartment by its worst item alone and never summing
  what was let through with a mitigation.
- Accepting a dripping material because it self-extinguished, without
  looking at what is mounted underneath it.

## Behavior contract (gate 3)

Entry and usage validation, partial-pressure comparison, configuration
coverage, the quantity exemption, containment handling, the four
dispositions, the severity roll-up and the compartment exception budget
are exercised by the gate 3 contract test:
scripts/test_q7021_manned_areas_interface.py against
scripts/q7021_manned_areas_interface_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7021_manned_areas_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
