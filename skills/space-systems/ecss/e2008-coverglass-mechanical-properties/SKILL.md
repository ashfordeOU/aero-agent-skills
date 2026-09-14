---
name: e2008-coverglass-mechanical-properties
description: "Use when a coverglass test matrix needs its mechanical record judged before the optical results are trusted. Document the dimensional and mass properties of every coverglass configuration on test under ECSS-E-ST-20-08C clause 8.7.4: place outline, thickness and mass inside their declared bands and name the state, derive the areal density the array mass budget consumes, cross-check the bulk density the four measurements imply against the declared glass material before any single band is believed, and refuse a configuration the test matrix declares but the record sheet omits. Trigger: ecss, e-st-20-08c-clause-8-7-4, coverglass-dimensional-record, coverglass-thickness-band, coverglass-areal-density-budget, coverglass-bulk-density-crosscheck, coverglass-configuration-record-completeness."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-mechanical-properties, coverglass-dimensional-record, coverglass-thickness-band, coverglass-areal-density-budget, coverglass-bulk-density-crosscheck, coverglass-configuration-record-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Coverglass Mechanical Properties (space-systems/ecss/e2008-coverglass-mechanical-properties)

Use when the task is the clause 8.7.4 mechanical record of
ECSS-E-ST-20-08C -- the outline, thickness and mass captured for each
coverglass configuration under test -- turned into a per-property
state, the derived densities the individual bands cannot give
themselves, and a verdict per configuration and across the matrix.

## Domain quick reference

- A coverglass campaign runs several configurations at once: a
  thickness family, a coating family, a doped and an undoped glass.
  Clause 8.7.4 is per configuration, so the unit of record is the
  configuration, and a test matrix with one configuration unrecorded
  has no mechanical record at all.
- Each family of measurement fails in its own way. An oversize outline
  overhangs the cell edge into the gap the interconnector needs; an
  undersize one leaves the cell perimeter bare to the environment;
  thickness is the shielding depth the radiation analysis assumed and
  the term that dominates coverglass mass; and mass is an array budget
  where a few per cent per piece becomes kilograms across a wing.
- A measurement has a state before it has a disposition. Within
  tolerance, above the upper limit and below the lower limit are three
  different engineering situations, and collapsing them into pass and
  fail loses the direction the deviation went in.
- There is no rework on a coverglass. Nothing can be machined back into
  tolerance without breaking the polish and the coating, so the middle
  disposition is a review band: a deviation outside the drawing band
  but inside a declared multiple of it is raised as a non-conformance
  and submitted for a use-as-is decision, and past that multiple the
  piece is refused.
- The four measurements are not independent. Mass over outline area is
  the areal density the array budget consumes; mass over full volume is
  the bulk density of the glass, which the material already fixes. A
  measured bulk density that departs from the declared material density
  says one of the four numbers is wrong -- a thickness read off the
  wrong datum, a chipped piece weighed short, or the wrong
  configuration on the sheet -- and that cross-check runs before any
  single band is believed.
- An unrecorded property is unknown, not conforming, and a record for a
  configuration the matrix never declared is a matrix mismatch rather
  than a deviation: there is no band to judge it against, and inventing
  one hides the mismatch.
- The mechanical record is what the optical and environmental results
  are later attributed to. A reflectance curve against a coverglass
  whose thickness nobody recorded belongs to no configuration.

## Workflow

1. Validate the matrix specification first: every configuration
   carrying all four bands, each with a nominal and a tolerance that
   leaves a real window, a declared glass material density, and a whole
   population of pieces.
2. Open each record against a configuration identifier and a sample
   identifier. A record with no traceable sample cannot be
   dispositioned, and a record naming an undeclared configuration is
   refused rather than folded in.
3. Place outline, thickness and mass inside their bands, recording the
   state and the margin to the nearest limit, not just a pass or a
   fail.
4. Derive the outline area, the areal density and the configuration's
   mass contribution at its declared population, because those are the
   numbers the array mass budget is written from.
5. Take the bulk density from mass, outline and thickness together,
   compare it with the declared material density, and raise the mutual
   inconsistency before trusting any individual band.
6. Roll the records up across the matrix: refuse a declared
   configuration nobody recorded, refuse two records claiming one
   sample, and let the worst record govern the matrix verdict.
7. Close with the matrix verdict, the out-of-band property names, the
   samples in review, the samples whose densities disagree and the
   total mass the matrix contributes.

## Pitfalls

- Recording one piece and calling the matrix covered. Clause 8.7.4 is
  per configuration, and the configuration nobody measured is the one
  the optical results will later be attributed to.
- Believing a band before the cross-check. A measured mass and a
  measured thickness that imply the wrong glass density are telling you
  the sheet is wrong, and every band read off that sheet inherits the
  error.
- Treating an out-of-band measurement as a scrap call. A coverglass
  cannot be reworked, but it can be submitted for use as is, and the
  review band is what separates that from a refusal.
- Quoting areal density as though it were the material density. One is
  mass over plan area and scales with thickness; the other is mass over
  volume and does not. Swapping them makes a thin coverglass look like
  a different glass.
- Reading an unrecorded property as conforming. Silence on a declared
  property is missing evidence, not a pass.
- Reporting only a verdict. A piece above its upper limit and a piece
  below its lower limit read the same on a summary line and lead to
  opposite recovery decisions.
- Comparing a measurement with a limit by bare arithmetic. A limit is a
  nominal plus a tolerance and a review limit multiplies that tolerance
  again, so a measurement meant to sit exactly on a limit can evaluate
  a few units in the last place to either side; the comparison absorbs
  that representation error while the limit stays untouched.

## Behavior contract (gate 3)

The band validation and state naming, the review band that stands in
for a rework a coverglass can never have, the outline area, areal
density and mass contribution, the bulk density cross-check against the
declared glass material, and the matrix rollup with its completeness
refusal are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_mechanical_properties.py against
scripts/e2008_coverglass_mechanical_properties_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_mechanical_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
