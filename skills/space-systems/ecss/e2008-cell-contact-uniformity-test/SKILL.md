---
name: e2008-cell-contact-uniformity-test
description: "Use when bare cell contact thickness maps are about to be accepted as qualification evidence of metallisation evenness. Assess whether the metallisation on a bare solar cell contact is laid to an even depth under ECSS-E-ST-20-08C clause 7.5.9: order a mapped set of thickness readings along one contact feature, refuse a map too sparse or too clustered to speak for the feature, reduce it to mean, range, coefficient of variation and a thinnest-to-thickest uniformity ratio, fit a slope along the feature to separate a plating gradient from random scatter or one thin spot, and roll the mapped features into a cell verdict. Trigger: ecss, e-st-20-08c-clause-7-5-9, bare-cell-contact-metallisation-uniformity, solar-cell-contact-thickness-map, contact-plating-thickness-gradient, cell-metallisation-uniformity-ratio, contact-thickness-coefficient-of-variation, bare-cell-grid-finger-thickness-spread."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e-st-20-08c-clause-7-5-9, e2008-cell-contact-uniformity-test, bare-cell-contact-metallisation-uniformity, solar-cell-contact-thickness-map, contact-plating-thickness-gradient, cell-metallisation-uniformity-ratio, contact-thickness-coefficient-of-variation, bare-cell-grid-finger-thickness-spread]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Contact Uniformity Test (space-systems/ecss/e2008-cell-contact-uniformity-test)

Use when the task is clause 7.5.9 of ECSS-E-ST-20-08C -- the
qualification measurement that confirms the metallisation deposited on
the contacts of a bare solar cell sits at an even depth everywhere it
was laid down. The clause is about evenness across one contact, not
about whether the contact is thick enough; that second question belongs
to the acceptance thickness measurement and is a different limit set.

## Domain quick reference

- The measurement is a map, not a reading. Thickness is taken at known
  positions along a contact feature -- a grid finger, a front or rear
  bus bar, the rear metallisation -- and the position is carried with
  the value because every useful conclusion is about how the value
  moves along the feature.
- A map that does not reach both ends of the feature describes the part
  of the contact it covers and nothing else. Six readings clustered in
  the first ten millimetres of a fifty millimetre bus bar return a
  flattering spread and say nothing about the far end, so the span the
  readings cover is checked against the feature length before any
  spread figure is trusted.
- Spread is reported three ways because a limit can be written against
  any of them: the coefficient of variation for the population, the
  thinnest-to-thickest uniformity ratio for the extremes, and the worst
  single departure from the mean for the one bad spot.
- The same coefficient of variation arrives from three different
  process faults. A mask or bath that drifted along the cell produces a
  gradient, agitation noise produces scatter, and a blocked nozzle
  produces one reading off an otherwise flat surface. Naming which one
  is present is what makes the result actionable on the line.
- A least-squares slope along the feature separates the first from the
  other two, and it is the end-to-end drift as a fraction of the mean
  that is compared, never the bare slope: half a micrometre per
  millimetre is nothing on a finger and severe on a bus bar.
- An outlier inflates any scale computed from a set it belongs to. At
  the handful of points this measurement runs at, the residual spread
  including the outlier is large enough to hide it from every
  threshold, so the scale is taken from the residuals with the largest
  one dropped.
- Two readings at the same position are a transcription fault rather
  than a repeat. They leave the position axis degenerate and no slope
  can be fitted through them.

## Workflow

1. Take the readings for one contact feature at a time and name the
   feature. A cell rolls up from its features; a spread figure that
   mixes a grid finger with a bus bar belongs to neither.
2. Order and validate the map: positions distinct and inside the
   declared feature length, thicknesses positive and finite. Refuse a
   bad map rather than flagging it, because every figure below it
   inherits the fault silently.
3. Check the map speaks for the feature -- enough points, and a span
   wide enough against the feature length -- and stop there if it does
   not. An inadequate map is neither a pass nor a fail and must not be
   reported as either.
4. Reduce to mean, range, coefficient of variation, uniformity ratio
   and the worst single departure, and compare each against its
   declared limit.
5. Fit the slope, normalise it to end-to-end drift over the mean, and
   name the dominant mode: a gradient, one outlier against a trimmed
   residual scale, or scatter.
6. Roll the features into a cell verdict where an inadequate map
   outranks a non-uniform one, since the second is a measured result
   and the first is an absence of one.

## Pitfalls

- Reading an average thickness as evidence of uniformity. The average
  of a contact thick at one end and thin at the other is exactly the
  average of an even one, which is the failure this clause exists to
  catch.
- Accepting a map clustered at one end. It returns a small spread
  honestly computed over the part of the contact it saw, and the
  reported figure carries no trace of the part it did not.
- Comparing a bare slope against a limit. The same micrometres per
  millimetre is negligible across a short finger and disqualifying
  across a long bus bar, so the drift is normalised over the feature
  before it is judged.
- Taking the outlier threshold against a residual scale the outlier is
  inside. At six points the inflated scale caps the achievable ratio
  below any sensible threshold, so a single thin spot is reported as
  ordinary scatter.
- Treating an inadequate map as a fail. It sends a good cell to scrap
  and it hides the real defect, which is the measurement plan.
- Clamping the fitted slope to a magnitude. The sign says which end of
  the cell ran thin, and that is the half of the result the plating
  line acts on.

## Behavior contract (gate 3)

Map ordering and validation, sample adequacy against feature length,
the spread statistics, signed point deviations, the least-squares
gradient with its plain and trimmed residual scales, the dominant
non-uniformity mode and the per-feature and per-cell verdicts are
exercised by the gate 3 contract test:
scripts/test_e2008_cell_contact_uniformity_test.py against
scripts/e2008_cell_contact_uniformity_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_cell_contact_uniformity_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
