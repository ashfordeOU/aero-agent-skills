---
name: q7080-dimensional-inspection
description: "Evaluate whether a dimensional inspection can actually decide the features it measures on an additively manufactured part. Use when a first article opens a part number, or a production lot is measured, under ECSS-Q-ST-70-80C inspection: combine repeatability and reproducibility into an expanded uncertainty, take its share of the tolerance band, pull the acceptance limits in by a guard band, sort each reading into conforming, indeterminate or non-conforming, then let demonstrated centred capability decide which features earn a reduced check once the first article has established a mean and a spread. Trigger: ecss, q-st-70-80-additive-manufacturing-scope, am-dimensional-inspection, first-article-dimensional-check, measurement-uncertainty-tolerance-ratio, dimensional-guard-band, am-process-capability-index, reduced-production-check."
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
  tags: [ecss, q-st-70-80-additive-manufacturing-scope, q7080-dimensional-inspection, am-dimensional-inspection, first-article-dimensional-check, measurement-uncertainty-tolerance-ratio, dimensional-guard-band, am-process-capability-index, reduced-production-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Dimensional Inspection (space-systems/ecss/q7080-dimensional-inspection)

Use when the task is the dimensional half of the ECSS-Q-ST-70-80C
inspection step -- the first-article check that opens a part number and
the reduced check that a demonstrated process later earns, on a part
that reached its size through a shrinking, distorting thermal history
and a surface that is rough before anything is machined.

## Domain quick reference

- Three questions decide a dimensional inspection, in this order: can
  the instrument see the tolerance, is the feature conforming, and how
  much has to be measured. Answering the second before the first is
  how an unusable instrument passes a part.
- Repeatability (one operator, one setup) and reproducibility (setup to
  setup, operator to operator) are independent sources, so they combine
  in quadrature before the coverage factor turns them into an expanded
  uncertainty. Adding them straight inflates the figure; quoting only
  repeatability hides the larger of the two.
- Measurement capability is that uncertainty as a share of the
  tolerance band, not an absolute number of micrometres. A one-tenth
  share is a capable measurement, a quarter is conditional, and beyond
  that the instrument is deciding nothing -- a wide tolerance can
  rescue a blunt instrument and a tight one can defeat a good one.
- Acceptance has to sit inside the drawing limits by at least the
  uncertainty. Without that guard band a part outside the drawing is
  accepted whenever the reading happens to fall inside it, and the
  narrower the band the more often that happens.
- A reading between the guarded and the drawing limits is neither a
  pass nor a fail. It is indeterminate, and it is closed by a better
  measurement or by an explicitly accepted risk, never by rounding.
- The first article is what makes a reduced production check possible:
  it establishes the mean and the spread from which centred capability
  is computed. Without a demonstrated mean and spread there is no
  capability, and no feature earns a reduction.
- Critical and interface features are measured every time regardless of
  capability, because the consequence of an escape, not the statistics,
  governs them.

## Workflow

1. Declare the stage. A first article measures every feature; a
   production lot measures only what the capability evidence has not
   released.
2. For each feature take the drawing limits, form the tolerance band,
   and reject an inverted or empty band rather than defaulting it.
3. Combine repeatability and reproducibility into an expanded
   uncertainty and take its share of the band. Reject a measurement
   with neither component characterized -- an uncharacterized
   instrument has no capability, which is not the same as a good one.
4. Pull the acceptance limits in by the uncertainty and reject the case
   where the guard band consumes the whole tolerance, because then no
   acceptance zone exists at all.
5. Sort each measured value into conforming, indeterminate or
   non-conforming against the guarded and drawing limits, and record
   the reason for every verdict that is not a clean pass.
6. For production, compute centred capability per feature and release
   only features that clear the declared threshold and are not critical
   or interface. Close with the part verdict: conforming, open, or
   non-conforming with the features named.

## Pitfalls

- Quoting an instrument's resolution as its uncertainty. Resolution is
  the last digit displayed; uncertainty is what the setup, the fixture,
  the operator and the thermal state add to it, and the gap between the
  two is usually an order of magnitude.
- Accepting a reading exactly on a drawing limit. That value is inside
  the guard band by definition, so it is an indeterminate result being
  recorded as a pass, and it is the single most common way an escape
  leaves a measurement room.
- Comparing capability ratios or capability indices by bare arithmetic.
  Both are quotients, so a feature meant to sit exactly on a threshold
  can land a few units in the last place on the wrong side; the
  comparisons absorb that representation error while the thresholds
  stay untouched.
- Carrying first-article capability into a build that changed. The mean
  and the spread belong to a machine, a parameter set, an orientation
  and a post-process route; change any of them and the reduced check
  rests on evidence from a different process.
- Measuring an as-built surface with contact probes and calling the
  scatter reproducibility. A rough skin moves the probe contact point
  from touch to touch, which is a real feature of the part, not an
  instrument problem, and it does not shrink with a better instrument.
- Treating a missing measurement as a pass. A feature with no value is
  open, and an empty field carries no information about conformance in
  either direction.

## Behavior contract (gate 3)

The uncertainty combination, capability ratio and grouping, guard-band
limits, feature verdicts, capability indices, stage scope and the part
verdict are exercised by the gate 3 contract test:
scripts/test_q7080_dimensional_inspection.py against
scripts/q7080_dimensional_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_dimensional_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
