---
name: q6005-radiographic-screening-inspection
description: "Evaluate the radiographic screening of a sealed hybrid package under ECSS-Q-ST-60-05C clause 10.3.10. Use when the task is deciding how many views the interior owes, showing the image can resolve the smallest rejectable feature, keeping beam transmission inside the band where a lid is neither opaque nor washed out, grading attachment voiding by total area, worst single void and what sits under the active area, and judging loose material by the conductor spacing it can span. Trigger: ecss, q-st-60-05c, hybrid-radiographic-screening, radiographic-view-coverage, radiographic-image-quality-percent, radiographic-beam-transmission-band, die-attach-void-area-limits, radiographic-foreign-material-bridging."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-radiographic-screening-inspection, hybrid-radiographic-screening, radiographic-view-coverage, radiographic-image-quality-percent, die-attach-void-area-limits, radiographic-foreign-material-bridging]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Screening — Radiographic Screening Inspection (space-systems/ecss/q6005-radiographic-screening-inspection)

Use when the task is the X-ray screen of ECSS-Q-ST-60-05C clause
10.3.10 — looking inside a sealed hybrid for voids, loose material and
misplaced elements without opening it, and judging whether the images
taken could have shown any of them.

## Domain quick reference

- A radiograph is a projection, so one view is a sample of the
  interior rather than a survey of it. A void behind a die, a strand of
  debris lying along the beam or an element displaced towards the
  camera is invisible in one direction and obvious in another. How many
  views the part owes comes from how it is built up, not from how long
  the exposure takes.
- An image has to be shown capable before it is read. Image quality is
  the smallest detail the system distinguishes as a fraction of the
  thickness it is looking through, and an image that cannot resolve the
  smallest rejectable feature returns clean views that carry no
  information about the part.
- Attenuation is exponential in thickness and specific to the material.
  The setting that images a moulded body is opaque through a kovar lid
  and has no contrast left through a thin epoxy one, so a usable
  radiograph sits inside a band at both ends and the band is checked,
  not assumed.
- Voiding is three objections, not one. The total voided fraction of a
  bond, the largest single void in it, and a void sitting under an
  active area are graded separately, and a bond can satisfy two of them
  while failing the third - a lightly voided attachment with one large
  void under the die is the common case.
- Loose material is graded by what it can reach. A particle matters
  once its largest dimension spans the smallest conductor spacing in
  the cavity; below that it is dirt, and above it is a short circuit
  waiting for the next shock.
- A displaced element is graded by the clearance it leaves, not by how
  far it moved. The same offset is trivial in a roomy cavity and closes
  the last of the clearance in a crowded one.

## Workflow

1. Validate each record: identifier, build style, the material layers
   the beam passes, views taken, the smallest detail resolved, bond
   area, the void areas, the void under the active area, the particle
   dimension, conductor spacing, nominal clearance, element offset and
   the minimum clearance. An unknown build style or material, a
   malformed layer, a non-positive thickness and voids totalling more
   than the bond they sit in are input errors.
2. Compare the views taken with the views the build style owes before
   reading any of them.
3. Sum the stack thickness, compute the transmitted fraction through
   it, and grade both the image quality percentage and the
   transmission band.
4. Grade voiding three ways against its three limits, absorbing each
   boundary with a named tolerance rather than by widening the limit.
5. Compare the largest particle dimension with the smallest conductor
   spacing, and report a bridging particle as its own finding.
6. Subtract the element offset from the nominal clearance and compare
   what is left with the minimum the design needs.
7. Aggregate the lot: accepted and rejected units, the reject fraction,
   the worst voiding anywhere in it, and the findings grouped by the
   unit that carried them.

## Pitfalls

- Taking one view and calling the interior inspected. The features the
  screen exists for hide behind other features, and the single view
  chosen is usually the one the assembly drawing shows.
- Reading an image nobody checked for quality. Without the smallest
  resolved detail against the thickness, a clean radiograph and an
  unreadable one look identical in the record.
- Carrying one exposure setting across package families. A kovar lid
  and a moulded body need very different beams, and the same setting
  gives a black image on one and a featureless grey on the other.
- Grading voiding on the total alone. A bond ten percent voided overall
  can have one void under the active area large enough to cook the die,
  and the total says nothing about it.
- Recording a particle as small because it is small relative to the
  cavity. The comparison that matters is with the conductor spacing it
  could land across.
- Judging a displaced element against a displacement limit. What the
  design cares about is the clearance left, and the same offset is
  acceptable in one cavity and not in another.

## Behavior contract (gate 3)

The view coverage rule, stack thickness and exponential transmission,
image quality percentage, the three void limits, the bridging particle
comparison, the clearance-after-offset check, indication grouping and
lot aggregation are exercised by the gate 3 contract test:
scripts/test_q6005_radiographic_screening_inspection.py against
scripts/q6005_radiographic_screening_inspection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_radiographic_screening_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
