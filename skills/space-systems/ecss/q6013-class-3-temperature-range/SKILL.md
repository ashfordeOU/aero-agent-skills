---
name: q6013-class-3-temperature-range
description: "Use when a datasheet band meets an application case before a Class 3 part is baselined. Evaluate whether the rated temperature limits of a commercial EEE part cover the application conditions at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.2.2.6: resolve the rated band from the temperature grade or the declared limits, widen the predicted extremes by the thermal analysis uncertainty, credit a correlated thermal model only down to its retained floor, take the cold end and the hot end apart, grade each against the thin margin this class owes, allow a bounded uprating or an approved hot-end mounting repair, and return one range verdict with the repair each short end needs. Trigger: ecss, q-st-60-13c-clause-6-2-2-6, class-three-rated-temperature-range, commercial-part-temperature-grade-band, thermal-model-correlation-credit, cold-end-hot-end-thermal-margin, hot-end-mounting-repair-credit, commercial-part-uprating-admissibility."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-temperature-range, class-three-rated-temperature-range, commercial-part-temperature-grade-band, thermal-model-correlation-credit, cold-end-hot-end-thermal-margin, hot-end-mounting-repair-credit, commercial-part-uprating-admissibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Temperature Range (space-systems/ecss/q6013-class-3-temperature-range)

Use when the task is clause 6.2.2.6 of ECSS-Q-ST-60-13C at the lowest
assurance class: a commercial part carries a rated temperature band, the
application carries an operating case, and the question is whether the
first covers the second with the margin this class owes.

## Domain quick reference

- The rated band belongs to the part type. It comes from the temperature
  grade the part is sold under, or from limits the declaration states
  outright, never from both -- two sources that disagree is the defect this
  check exists to catch, not a detail to reconcile quietly.
- The application case is not the predicted extremes. The thermal analysis
  behind those extremes carries an uncertainty, and that uncertainty widens
  the case outwards at both ends before anything is compared. Comparing a
  datasheet band against an un-widened prediction is the usual way a part
  looks covered and is not.
- This class lets a correlated thermal model buy part of that uncertainty
  back. Where the model has been correlated against a thermal balance test,
  the declared uncertainty is reduced by a fixed credit, down to a retained
  floor that is never crossed. Correlation narrows the unknown; it does not
  remove it, and a model nobody correlated keeps the whole of its declared
  figure.
- The cold end and the hot end are graded separately. They fail for different
  reasons and they are repaired in different ways: a hot end is often bought
  back by the mounting and the conduction path, a cold end almost never is.
  A single worst-case number hides which end is the problem.
- The margin owed at this class is the thinnest of the three, but it is not
  zero. An end sitting inside the rated band and short of that margin is
  still a finding, because the margin is what absorbs the drift the analysis
  did not model and the spread the manufacturer never guaranteed.
- A zero margin is short, not covered. An end that lands exactly on the rated
  limit has nothing between it and the limit.
- Two credits may move an end and neither is free. An uprating evaluation may
  extend a rated end, bounded and evidenced; an unevidenced claim earns
  nothing and is reported. An approved mounting and conduction-path repair
  may pull the hot extreme back in, bounded, and at the hot end alone -- the
  cold extreme is set by the environment the part sits in, and no mounting
  change reaches it.
- A covered range carrying either credit is not a clean one. Both are open
  actions that travel with the part into the build.

## Workflow

1. Resolve the rated band from the part declaration, rejecting a declaration
   that names a grade and explicit limits together or neither of them.
2. Reduce the declared thermal analysis uncertainty by the correlation credit
   where the model has been correlated by test, never below the retained
   floor, and keep the declared figure where it has not.
3. Widen the predicted application minimum and maximum by the resulting
   uncertainty to get the case the part actually has to survive.
4. Validate any uprating declaration, credit it only when it is evidenced and
   inside the bound, cap it when it is not, and apply the credited extension
   to the ends the claim names.
5. Validate any mounting and conduction-path repair, refuse it outright at
   the cold end, credit it only when it is approved and inside the bound, and
   pull the hot extreme in by the credited amount.
6. Compute the cold-end and hot-end margins against the effective rated
   limits, keeping the two ends apart.
7. Grade each end -- covered with margin, short of the margin, or not covered
   at all -- rank the short ends by how far each is from the required margin,
   and name the verdict, carrying every credit and finding with it.

## Pitfalls

- Comparing the datasheet band against the predicted extremes and skipping
  the analysis uncertainty, so a part that is marginal reads as covered.
- Taking the correlation credit on a model nobody correlated by test, or
  taking it past the retained floor. The floor is there because correlation
  narrows the unknown rather than closing it.
- Collapsing the two ends into one worst-case margin, which hides the end
  that drives the repair.
- Claiming a mounting repair at the cold end. A conduction path reaches a hot
  part; the cold extreme belongs to the environment and is repaired by the
  part selection, the duty cycle or a heater, never by the mounting.
- Reading a zero margin as a pass because the case is technically inside the
  band. The margin requirement is the point of the check, thin though it is
  at this class.
- Taking an uprating claim on the strength of the number alone. Without the
  evaluation behind it the extension is an assertion, not evidence, and
  letting it run as far as the analysis needs ignores the bound the physics
  imposes.
- Treating a covered range that carries a credit as clean. Both credits are
  open actions and have to travel with the part.
- Adjusting the rated band to suit the application rather than adjusting the
  mounting, the duty cycle or the part selection.

## Behavior contract (gate 3)

The grade band resolution, correlation credit and retained floor, uncertainty
widening, per-end margin, end disposition, uprating admissibility and bound,
hot-end mounting repair credit, shortfall ranking and range verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_3_temperature_range.py against
scripts/q6013_class_3_temperature_range_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_temperature_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
