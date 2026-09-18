---
name: q7080-density-and-porosity-control
description: "Assess the density and porosity of additively manufactured material against its acceptance limits. Use when a build has to be graded on soundness rather than on strength: turn the dry and suspended weighings into a bulk density, express it against the reference alloy density and read the porosity from it, grade the largest pore against whichever of the drawing limit and the wall-fraction limit is smaller, refuse a tomography scan that resolves coarser than the limit it grades, compare buoyancy with the sectioned value, then take the worst and name it. Trigger: ecss, q-st-70-80-additive-manufacturing, am-relative-density-acceptance, am-archimedes-bulk-density, am-lack-of-fusion-pore-size, am-ct-pore-population, am-porosity-wall-fraction-limit."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-density-and-porosity-control, am-relative-density-acceptance, am-archimedes-bulk-density, am-lack-of-fusion-pore-size, am-ct-pore-population, am-porosity-wall-fraction-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Density and Porosity Control (space-systems/ecss/q7080-density-and-porosity-control)

Use when the quality clause of ECSS-Q-ST-70-80 is the task: deciding
whether additively manufactured material is dense enough, whether the
pores it does carry are small enough for the section they sit in, and
whether the inspection that looked for them could have found them.

## Domain quick reference

- Bulk density and pore size are two requirements on the same material
  and they fail separately. A part can sit well above its relative
  density floor and still carry one lack-of-fusion defect that is the
  critical flaw for the part.
- The buoyancy measurement gives a bulk density for the whole part. It
  becomes a requirement only once it is expressed against the reference
  density of the alloy, and one minus that fraction is the porosity
  carried.
- A part reading denser than the reference is not an unusually good
  part. It means the reference value or the weighing is wrong, and the
  measurement cannot be graded until that is resolved.
- The governing pore limit is the smaller of the drawing limit and a
  fraction of the local wall. On a thin section the wall sets it, and a
  pore that passes on a thick boss fails in a web.
- A tomography scan has a detection limit, and a scan that resolves
  coarser than the size limit it is meant to grade cannot find the
  defect it is looking for. A clean result from such a scan is silence,
  not evidence.
- The count of resolved indications is a process quantity separate from
  their size. A population that has doubled while every pore is still
  inside the limit says the parameter set has moved.
- Buoyancy and a sectioned micrograph do not count the same porosity:
  surface-connected pores fill with fluid and read as solid. A gap
  between the two methods beyond the declared tolerance is a
  measurement finding, not a rounding difference.

## Workflow

1. Form the bulk density from the dry and suspended weighings and the
   fluid density, refusing a suspended mass that is not below the dry
   mass as an unusable measurement.
2. Express it against the reference alloy density as a relative density,
   refusing an overshoot beyond weighing scatter rather than reporting a
   part denser than the alloy.
3. Grade the relative density against its floor and report the porosity
   it implies, calling out a result that clears the floor by almost
   nothing as a build with no margin.
4. Resolve the governing pore limit as the smaller of the drawing limit
   and the wall fraction, then grade the largest pore against it and
   report which of the two governed.
5. Grade the tomography population: discard indications below the
   detection limit but count them, reject any indication above the size
   limit, reject a scan whose detection limit is coarser than that size
   limit, and review a resolved count above the allowance.
6. Where a sectioned value exists, compare it with the buoyancy fraction
   and raise a disagreement beyond tolerance for review.
7. Take the worst of relative density, pore size, pore population and
   method agreement as the verdict, name the characteristic that drove
   it, and grade every on-limit value with the tolerant comparison.

## Pitfalls

- Reporting a density in grams per cubic centimetre and calling it an
  acceptance result. Only the fraction of the reference density is a
  requirement, and only that fraction gives the porosity.
- Reading a relative density above one as a very dense part. It is an
  inconsistent record between the weighing and the reference, and it
  usually means the reference is for a different temper or alloy.
- Grading every pore against the drawing limit alone. In a thin web the
  wall fraction governs, and the same pore is acceptable in a boss and a
  reject in the web beside it.
- Accepting a clean tomography result without checking what the scan
  could resolve. A scan coarser than the limit it grades returns
  nothing, and nothing looks exactly like a sound part.
- Ignoring indications below the detection limit entirely. They are not
  gradable, but their count is part of the record, and dropping them
  silently makes an unresolvable population look empty.
- Reading a rising indication count as acceptable because each pore is
  small. Size and population are separate quantities and the population
  moves first.
- Treating a buoyancy and a section that disagree as a rounding issue.
  The two methods count surface-connected porosity differently, so the
  gap is evidence about the part or the measurement, not noise.

## Behavior contract (gate 3)

The buoyancy density, relative density and porosity, the governing pore
limit, the largest-pore grading, the tomography population and detection
limit, and the two-method agreement are exercised by the gate 3 contract
test:
scripts/test_q7080_density_and_porosity_control.py against
scripts/q7080_density_and_porosity_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_density_and_porosity_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
