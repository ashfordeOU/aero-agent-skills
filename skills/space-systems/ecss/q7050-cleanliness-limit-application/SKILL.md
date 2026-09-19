---
name: q7050-cleanliness-limit-application
description: "Determine which particle cleanliness level a hardware item or facility may be released against under ECSS-Q-ST-70-50C. Use when a size-resolved particle count per unit area has been obtained, the programme names a product cleanliness level or a facility class, and the counts must be graded against the whole level curve rather than one convenient size. Evaluates the allowance at every counted channel, scales it from the reference area onto the area inspected, finds the smallest level enveloping the distribution, names the size channel that drives the result, and grades airborne concentrations against the facility class curve. Trigger: ecss, q-st-70-50, product-cleanliness-level, particle-count-per-area, level-curve-envelope, driving-size-channel, facility-air-class-curve, cleanliness-level-assignment."
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
  tags: [ecss, q-st-70-cleanliness-monitoring-scope, q7050-cleanliness-limit-application, product-cleanliness-level, particle-count-per-area, level-curve-envelope, driving-size-channel, facility-air-class-curve]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Monitoring — Limit and Level Application (space-systems/ecss/q7050-cleanliness-limit-application)

Use when the task is applying the ECSS-Q-ST-70-50C cleanliness limits to a
monitoring result — deciding whether a size-resolved particle count meets
the level the programme assigned to that hardware or facility, and which
level it would actually support.

## Domain quick reference

- A cleanliness level is a curve, not a count. Its label is the largest
  particle size it admits at all, and the allowance at smaller sizes
  rises steeply below that label. Grading a distribution therefore means
  grading every counted channel; a single size can conform while the
  item as a whole does not.
- The allowance is quoted per a reference area. An inspection that
  covers a different area is graded against the allowance scaled to the
  area actually inspected — comparing a raw count from a small coupon
  with a reference-area allowance grades the coupon as clean whatever it
  carried.
- Counts over size are cumulative and therefore non-increasing: a
  channel reporting more particles at a larger size than at a smaller
  one is a data-entry or binning defect, and grading it produces a level
  no re-inspection will reproduce.
- Assigning a level to a measured distribution is the inverse problem:
  for each counted point find the smallest level whose curve lies above
  it, and take the largest of those. The channel that produced the
  largest is the driver, and it is the one a cleaning improvement has to
  move.
- A facility class governs airborne concentration per unit volume on the
  same falling-with-size shape. It is a separate grading from the
  surface level and neither substitutes for the other: a compliant room
  does not make a contaminated surface conforming.

## Workflow

1. Validate the observations: positive sizes, integer non-negative
   counts, no repeated channel, and cumulative counts that do not rise
   with size.
2. For each counted channel, evaluate the level curve allowance at that
   size and scale it from the reference area to the inspected area.
3. Grade each channel, recording the allowance, the utilisation and
   whether the channel conforms, and absorb an exact equality at the
   allowance with a named tolerance rather than by loosening the level.
4. Invert the curve per point to get the smallest level each point
   demands, take the largest, and record the driving size channel.
5. When the programme assigned a level, grade the whole distribution
   against it and list every failing channel.
6. When a facility class applies, grade the airborne concentrations
   against the class curve at each measured size.
7. Report the envelope level, the assigned-level grading, the facility
   grading and every finding.

## Pitfalls

- Grading only the largest counted size. The level curve is steepest
  near its label, so the smaller channels carry the larger allowances
  and are usually where a marginal item actually fails.
- Comparing a coupon count with a reference-area allowance. The
  allowance has to be scaled onto the inspected area first, or a small
  sample is graded clean and a large one dirty for identical hardware.
- Reading the level label as a count limit. The label is a size; the
  count it admits at that size is one particle, and everything else on
  the curve follows from the shape, not from the label.
- Substituting the facility class for the surface level. Airborne
  cleanliness governs the deposition rate, not the accumulated surface
  loading, and a clean room over a long exposure still dirties hardware.
- Loosening the assigned level so a marginal channel passes. An
  equality at the allowance is a representation question, handled by
  the tolerance inside the comparison; the assigned level stays as the
  programme set it.

## Behavior contract (gate 3)

The observation validation, level-curve allowance, area scaling,
per-channel grading, envelope inversion and facility-class grading are
exercised by the gate 3 contract test:
scripts/test_q7050_cleanliness_limit_application.py against
scripts/q7050_cleanliness_limit_application_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7050_cleanliness_limit_application.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
