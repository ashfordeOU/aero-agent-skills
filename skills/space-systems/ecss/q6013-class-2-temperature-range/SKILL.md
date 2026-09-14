---
name: q6013-class-2-temperature-range
description: "Verify that the rated temperature limits of a commercial EEE part cover the mission operating case at the intermediate assurance class of ECSS-Q-ST-60-13C clause 5.2.2.6: resolve the rated band from the temperature grade or the declared limits, widen the predicted mission extremes by the thermal analysis uncertainty, take the cold end and the hot end separately, grade each against the margin the class owes, credit an uprating extension only where it is bounded and evidenced, and return one range verdict with the repair each short end needs. Use when a datasheet band has to be reconciled with a thermal case before a part is baselined. Trigger: ecss, q-st-60-13c-clause-5-2-2-6, class-two-rated-temperature-range, commercial-part-temperature-grade-band, thermal-analysis-uncertainty-widening, cold-end-hot-end-thermal-margin, commercial-part-uprating-admissibility."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-2-temperature-range, class-two-rated-temperature-range, commercial-part-temperature-grade-band, thermal-analysis-uncertainty-widening, cold-end-hot-end-thermal-margin, commercial-part-uprating-admissibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Temperature Range (space-systems/ecss/q6013-class-2-temperature-range)

Use when the task is clause 5.2.2.6 of ECSS-Q-ST-60-13C at the intermediate
assurance class: a commercial part carries a rated temperature band, the
mission carries an operating case, and the question is whether the first
covers the second with the margin the class owes.

## Domain quick reference

- The rated band belongs to the part type. It comes from the temperature
  grade the part is sold under, or from limits the declaration states
  outright, never from both -- two sources that disagree is the defect this
  check exists to catch, not a detail to reconcile quietly.
- The mission case is not the predicted extremes. The thermal analysis behind
  those extremes carries an uncertainty, and that uncertainty widens the case
  outwards at both ends before anything is compared. Comparing a datasheet
  band against an un-widened prediction is the usual way a part looks covered
  and is not.
- The cold end and the hot end are graded separately. They fail for different
  reasons and they are repaired in different ways: a hot end is often bought
  back by the mounting and the conduction path, a cold end almost never is.
  A single worst-case number hides which end is the problem.
- Containment is not enough at the intermediate class. An end sitting inside
  the rated band but short of the required margin is a finding, because the
  margin is what absorbs the drift the analysis did not model and the spread
  the manufacturer never guaranteed.
- A zero margin is short, not covered. An end that lands exactly on the rated
  limit has nothing between it and the limit.
- An uprating claim may extend a rated end, but only when the extension is
  bounded and an uprating evaluation stands behind it. An unevidenced claim
  earns nothing and is reported. An evidenced one earns its extension and
  still leaves a finding, because the credit travels with the part.

## Workflow

1. Resolve the rated band from the part declaration, rejecting a declaration
   that names a grade and explicit limits together or neither of them.
2. Widen the predicted mission minimum and maximum by the thermal analysis
   uncertainty to get the case the part actually has to survive.
3. Validate any uprating declaration, credit it only when it is evidenced and
   inside the bound, cap it when it is not, and apply the credited extension
   to the ends the claim names.
4. Compute the cold-end and hot-end margins against the effective rated
   limits, keeping the two ends apart.
5. Grade each end: covered with margin, short of the margin, or not covered
   at all.
6. Rank the short ends by how far each is from the required margin, so the
   worst end leads the repair list.
7. Name the verdict -- not covering while any end is outside the band, margin
   short while any end is inside but short, covers only when neither is true
   -- and carry the findings with it.

## Pitfalls

- Comparing the datasheet band against the predicted extremes and skipping
  the analysis uncertainty, so a part that is marginal reads as covered.
- Collapsing the two ends into one worst-case margin, which hides the end
  that drives the repair.
- Reading a zero margin as a pass because the case is technically inside the
  band. The margin requirement is the point of the check.
- Taking an uprating claim on the strength of the number alone. Without the
  evaluation behind it the extension is an assertion, not evidence.
- Letting an uprating extension run as far as the analysis needs. The bound
  exists because the physics stops being extrapolable well before that.
- Treating a covered range that carries an uprating credit as clean. The
  credit is an open action and has to travel with the part.
- Adjusting the rated band to suit the mission rather than adjusting the
  mounting, the duty cycle or the part selection.

## Behavior contract (gate 3)

The grade band resolution, uncertainty widening, per-end margin, end
disposition, uprating admissibility and bound, shortfall ranking and range
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_temperature_range.py against
scripts/q6013_class_2_temperature_range_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_2_temperature_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
