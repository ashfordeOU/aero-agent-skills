---
name: q7040-ndt-of-brazements
description: "Determine the non-destructive test set a brazement owes at inspection, using the ECSS-Q-ST-70-15C methods the brazing standard calls up. Use when a brazed joint has a geometry, an access condition, a wall thickness and a hermeticity requirement, and the volumetric method, the coverage and the sample size all still have to be fixed. Routes coverage demonstration to radiography or to ultrasonics by what the joint plane and the access actually allow, adds a leak test wherever hermeticity is required, escalates an unreachable joint to process control with witness coupons, and confirms the chosen method resolves the void the class accepts. Trigger: ecss, q-st-70-40-brazing-scope, brazement-ndt-method-selection, braze-coverage-radiography, braze-lap-joint-ultrasonics, brazement-hermeticity-leak-test, braze-ndt-sample-size, braze-witness-coupon-escalation."
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
  tags: [ecss, q-st-70-40-brazing-scope, q7040-ndt-of-brazements, brazement-ndt-method-selection, braze-coverage-radiography, braze-lap-joint-ultrasonics, brazement-hermeticity-leak-test, braze-ndt-sample-size, braze-witness-coupon-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — NDT of Brazements (space-systems/ecss/q7040-ndt-of-brazements)

Use when the task is the inspection step for a brazed joint -- choosing
which of the ECSS-Q-ST-70-15C non-destructive methods the brazement
actually owes, how much of the lot they have to cover, and whether the
method chosen can resolve the smallest indication the acceptance class
still rejects.

## Domain quick reference

- Visual inspection is never the whole answer and never optional. It
  sees the fillet and the flow at the joint mouth, which is evidence
  about wetting but says nothing about what the capillary gap did in
  the middle of the overlap. Coverage of the gap is a volumetric
  question.
- Radiography and ultrasonics do not substitute for each other; the
  joint plane decides. Radiography reads a density change along the
  beam, so it resolves a braze gap the beam runs along -- a butt or a
  sleeve joint -- and is nearly blind to a thin unbonded layer in a
  lap joint lying across the beam. Ultrasonics reads a reflection off
  that same unbonded layer, so the lap joint radiography cannot see is
  the case ultrasonics is for.
- Access is a hard constraint, not a preference. Radiography needs a
  path for the source and the film or panel on opposite sides.
  Ultrasonics needs one coupling surface parallel to the joint. A
  joint with neither has no volumetric method at all, and the
  inspection obligation then moves upstream into process control and
  destructively sectioned witness coupons brazed in the same run.
- Thickness bounds both methods from opposite ends. Radiographic
  sensitivity is a fraction of the penetrated thickness, so a thick
  section stops resolving small voids; ultrasonics needs enough sound
  path to separate the joint echo from the entry surface, so a very
  thin section stops resolving anything at all.
- Hermeticity is a separate requirement with a separate test. A joint
  can be volumetrically sound and still leak along a continuous path
  no void criterion catches, so a pressurised or sealed brazement
  carries a leak test on top of whatever volumetric method it uses.
- Coverage follows the class, and the sample size follows the lot. The
  top class is inspected throughout; the lower classes are sampled at
  a declared fraction with a floor, and a fraction that rounds to less
  than the floor does not shrink the sample.
- The method has to out-resolve the acceptance limit. If the smallest
  void the method can detect is larger than the largest void the class
  accepts, a clean report means nothing, and an indication exactly at
  the resolution limit counts as detected -- the two numbers are
  products of measured quantities and the comparison absorbs their
  representation error.

## Workflow

1. Normalise the brazement: joint geometry, access condition, wall
   thickness, acceptance class, hermeticity requirement and lot size.
   Reject an unrecognised value rather than defaulting it.
2. Put visual inspection on the list unconditionally.
3. Decide whether a volumetric method is owed at all -- the top two
   classes and any joint with a declared coverage requirement owe one.
4. Test radiography and ultrasonics in turn against the joint plane,
   the access and the thickness window; take the admissible one, take
   ultrasonics where both are admissible on a lap-type plane, and
   escalate to process control with witness coupons where neither is.
5. Add a leak test wherever the joint is hermetic or pressurised.
6. Compute the coverage: full inspection for the top class, otherwise
   the sampled count from the lot size, the declared fraction and the
   floor.
7. Compare the smallest void the chosen method resolves against the
   largest void the class accepts and raise a finding where the method
   cannot see the defect it is supposed to reject.

## Pitfalls

- Radiographing a lap joint and reporting it sound. A disbond parallel
  to the beam changes the absorbed path length by almost nothing, so
  the radiograph is clean whether the joint is fully brazed or barely
  tacked at the edges.
- Reading a visual fillet as coverage. A continuous, well-formed
  fillet all the way round is evidence the filler wetted the mouth of
  the gap; it is routinely present on joints whose centre never
  filled.
- Treating a leak test as a volumetric result. A leak test integrates
  the whole boundary and passes a joint with large isolated voids that
  happen not to connect, and fails a joint with tiny but connected
  porosity; it answers hermeticity and nothing else.
- Sampling a lot by a percentage without a floor. Ten percent of a lot
  of four is a single joint, which is not a sample of anything, and it
  is exactly the lot size where a process excursion goes unseen.
- Choosing a method without checking what it can resolve. A thick
  section radiographed at two percent sensitivity cannot see the void
  a tight class rejects, so the report is clean by construction and
  the inspection has verified only that the equipment was switched on.

## Behavior contract (gate 3)

Brazement normalisation, volumetric method admissibility, the witness
coupon escalation, the leak-test addition, sample-size computation and
the resolution-against-acceptance comparison are exercised by the gate
3 contract test: scripts/test_q7040_ndt_of_brazements.py against
scripts/q7040_ndt_of_brazements_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7040_ndt_of_brazements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
