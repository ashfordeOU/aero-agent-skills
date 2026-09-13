---
name: e2008-photovoltaic-assembly-scope-description
description: "Define the extent of the photovoltaic assembly and the array configurations addressed, anchored at ECSS-E-ST-20-08C clause 5.1.1. Use when an array wing declaration has to be scoped before its provisions are applied: place each named element inside the assembly, on its boundary of supply or outside it altogether, confirm the declaration names the connector or mounting interface at which the assembly stops, derive the configuration family from mounting, substrate, deployment kinematics and concentration ratio rather than from a label, separate the flat-plate families the clause addresses from a concentrating array it hands over, and check the provisions the family pulls in against those the declaration carries. Trigger: ecss, e-st-20-08c, photovoltaic-assembly-scope, photovoltaic-assembly-boundary, solar-array-configuration-family, array-boundary-of-supply, flat-plate-versus-concentrator-array, deployable-solar-array-provisions, solar-array-element-placement, flexible-blanket-array-configuration."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-photovoltaic-assembly-scope-description, photovoltaic-assembly-scope, photovoltaic-assembly-boundary, solar-array-configuration-family, array-boundary-of-supply, flat-plate-versus-concentrator-array, solar-array-element-placement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Photovoltaic Assembly Scope Description (space-systems/ecss/e2008-photovoltaic-assembly-scope-description)

Use when the task is the scope statement of ECSS-E-ST-20-08C clause 5.1.1
-- what the photovoltaic assembly actually covers, where it stops, and
which array configurations the provisions that follow are written for.

## Domain quick reference

- The assembly is a boundary of supply, not a list of interesting parts.
  Everything that converts, protects, interconnects, insulates or carries
  the cell field is inside it: cell, coverglass and its adhesive,
  interconnects, bus bars, string wiring, bypass diodes, the substrate
  facesheet and core, and the insulation between circuit and substrate.
- Three elements are the boundary itself rather than contents: the array
  connector, where the electrical assembly ends and the spacecraft
  harness begins; the panel mounting interface, where the mechanical
  assembly ends; and the temperature-sensor interface, where the
  instrumentation does. A declaration that names none of them has no
  stated end, and its extent cannot be read from it at all.
- Everything past those interfaces is somebody else's: hinges and
  hold-down releases belong to the deployment mechanism, the yoke to the
  array structure, the drive mechanism to the pointing chain, the
  conditioning unit to the power subsystem. A declaration that claims
  them is not being thorough, it is taking on verification it will be
  held to.
- The configuration family is derived from what the array is, never from
  what the drawing calls it. Four attributes settle it: how it is
  mounted, whether the substrate is rigid or flexible, whether it
  deploys and by what kinematics, and how much it concentrates.
- Some attribute combinations are contradictions rather than unusual
  designs: a flexible substrate that never deploys has nothing to
  tension it, a flexible blanket is carried on a wing rather than
  wrapped on a body or a drum, and a body-mounted array does not deploy.
  Reject those as malformed input instead of grouping them somewhere.
- The clause addresses the flat-plate families -- body-mounted, spinner
  drum, rigid deployable panel, flexible deployable blanket. A
  concentrating array is derived here so that it is recognised and
  handed over with its optics provisions named, not so that it is
  silently treated as a flat plate with a bigger number on it.
- The family and the element list have to agree. A tensioned blanket has
  no stiff core to bend, so a substrate core declared on one is a
  contradiction between the two halves of the declaration and neither
  half alone reveals it.
- Every family carries the common provisions; the family adds its own.
  Deployment loading follows anything that deploys, tensioning and
  stowage follow a blanket, structure thermal coupling follows a
  body-mounted array, spin-modulated illumination follows a drum.
- A concentration ratio of exactly one is a flat plate. A ratio computed
  upstream can land a few units in the last place above one; absorb that
  in the comparison rather than declaring a concentrator.

## Workflow

1. Normalize the wing declaration: identifier, element list, attribute
   set, and optionally the provisions the declaration claims to carry.
   Reject an unknown key, a missing required key and a blank identifier.
2. Place every named element inside, on the boundary, or outside, and
   reject an unknown or repeated element name.
3. Confirm the declaration names at least one boundary element and at
   least one solar cell; without the first it has no stated end, without
   the second it is not a photovoltaic assembly.
4. Flag every element that falls outside the assembly.
5. Derive the configuration family from mounting, substrate, deployment
   and concentration ratio, rejecting a contradictory attribute set.
6. If the family is a concentrating one, hand it over and name the
   optics provisions it goes with.
7. Cross-check the element list against the family and flag an element
   the family cannot carry.
8. Assemble the applicable provisions and, if the declaration claims a
   provision set, name every applicable one it does not carry.
9. Aggregate across the wings: reject a duplicate identifier, report the
   families present, flag a mixed-configuration array, report the
   in-scope fraction and accept only when no finding remains.

## Pitfalls

- Reading the assembly as "the panel" and pulling in the hinges, the
  yoke and the drive mechanism -- each one imports a verification the
  assembly supplier never agreed to carry.
- Leaving the array connector out of the element list because it is an
  interface rather than a part; the interface is precisely what fixes
  where the assembly stops.
- Taking the configuration from the programme's own name for the wing. A
  wing called a panel that carries a tensioned blanket obeys the blanket
  provisions, and only the attributes reveal that.
- Grouping a contradictory attribute set into the nearest family instead
  of rejecting it -- a non-deploying flexible substrate is a data error,
  and a family assigned to it will be quietly wrong everywhere it is
  used afterwards.
- Treating a concentrating array as a flat plate with a larger flux. Its
  optics alignment and off-pointing thermal margin come from elsewhere,
  and this clause's job is to say so rather than absorb it.
- Checking the attribute set and the element list separately. A blanket
  declared with a rigid substrate core passes both halves on its own and
  fails only when they are read together.
- Declaring a concentrator because a ratio computed upstream sits a few
  units in the last place above one; absorb the representation error in
  the comparison.

## Behavior contract (gate 3)

The element placement, the boundary-of-supply grouping, the configuration
family derivation and its contradiction rejections, the addressed-family
separation, the family-to-element cross-check, the provision coverage and
the multi-wing acceptance are exercised by the gate 3 contract test:
scripts/test_e2008_photovoltaic_assembly_scope_description.py against
scripts/e2008_photovoltaic_assembly_scope_description_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_photovoltaic_assembly_scope_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
