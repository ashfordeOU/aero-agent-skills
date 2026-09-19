---
name: q7005-equipment-control
description: "Audit the spectrometer, the measurement cells and the sampling consumables an infrared contamination analysis rests on. Use when a run under ECSS-Q-ST-70-05C has to be cleared before a sample is taken: walk each calibration and each consumable shelf life forward by whole calendar months so a month end lands where the calendar puts it, report the days left on the analysis day rather than on today, weigh the wavenumber tolerance against the uncertainty that polices it, grade a cell pathlength as a fraction of nominal, and refuse a cell or wipe blank that sits too close to the quantitation limit beside it. Trigger: ecss, q-st-70-05-ir-contamination-scope, ir-spectrometer-calibration-currency, measurement-cell-pathlength-verification, sampling-consumable-shelf-life, precleaned-consumable-blank-level, wavenumber-tolerance-uncertainty-ratio."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-equipment-control, ir-spectrometer-calibration-currency, measurement-cell-pathlength-verification, sampling-consumable-shelf-life, precleaned-consumable-blank-level, wavenumber-tolerance-uncertainty-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Equipment Control (space-systems/ecss/q7005-equipment-control)

Use when the task is the quality-assurance step that clears the hardware
an ECSS-Q-ST-70-05C infrared contamination analysis depends on — the
spectrometer, the measurement cells and the precleaned consumables the
sample will touch — before anything is sampled.

## Domain quick reference

- A calibration interval is counted in calendar months, not in a fixed
  number of days. Twelve months from the last day of January is the last
  day of January, and the end of February moves with the leap year. A
  365-day addition lands a day out at every month end and the error is
  invisible until an audit asks which certificate was current.
- Currency is asked about the analysis day, not about today. A
  certificate that expires during a campaign was already short on the
  day the campaign started, and the days left on the run day is the
  number the record has to carry.
- Accuracy is a ratio. The wavenumber uncertainty is meaningless on its
  own; it is capable when the tolerance it has to police is several
  times larger. Quoting the uncertainty alone is the most common way a
  marginal instrument clears a review.
- A cell has geometry as well as a certificate. A pathlength that has
  drifted scales every concentration read through that cell in one
  direction, so the deviation is graded as a fraction of nominal and not
  as an absolute number of micrometres.
- Everything the sample touches brings its own organic background. A
  cell blank or a wipe blank is graded against the quantitation limit it
  sits beside, because a blank of comparable size does not add noise to
  the measurement, it consumes it.
- Consumables expire too. A precleaning certificate names a lot, and the
  lot has a shelf life counted in the same calendar months as an
  instrument interval. An expired lot is a blocked item, not a note in
  the margin, because its cleanliness is exactly what was being relied
  on.
- An item close to expiry is cleared and watched rather than blocked.
  Collapsing that into a pass loses the warning; collapsing it into a
  failure stops runs that are entitled to proceed.

## Workflow

1. Resolve the policy: the minimum capability ratio, the largest blank
   fraction tolerated beside a quantitation limit, the pathlength
   tolerance fraction and the watch window, refusing an unknown key
   rather than silently ignoring it.
2. Validate each item against the fields its kind actually owes, so a
   spectrometer is never failed for a missing pathlength.
3. Advance each calibration date, and each consumable lot release date,
   by whole calendar months and clamp to the month end.
4. Take the days left on the analysis day, negative once the date has
   passed.
5. For the spectrometer, divide the wavenumber tolerance by its
   uncertainty and compare with the capability floor, absorbing
   representation error at the boundary rather than relaxing the floor.
6. For a cell, take the pathlength deviation as a fraction of nominal
   and compare with the tolerance fraction.
7. For a cell or a consumable, take the blank as a fraction of the
   quantitation limit and compare with the permitted share.
8. Verdict per item: blocked on any finding, cleared with watch inside
   the watch window, cleared otherwise; then decide whether the run may
   proceed at all.

## Pitfalls

- Adding 365 days for a twelve-month interval. Month-end certificates
  land a day out, and the whole audit trail inherits the error.
- Checking currency on the day the question is asked. The run day is the
  only day that matters, and a campaign spanning an expiry has to be
  split.
- Quoting an uncertainty without the tolerance beside it. A small
  uncertainty is not capability; the ratio is.
- Grading a pathlength drift in micrometres. The same two micrometres
  are negligible on a thick cell and disqualifying on a thin one.
- Treating a blank as background to subtract rather than as a limit on
  what can be measured. Once the blank approaches the quantitation limit
  there is no measurement left to correct.
- Blocking an item merely because its certificate expires soon. The
  watch verdict exists so that the warning survives without stopping a
  run that is still entitled to proceed.

## Behavior contract (gate 3)

The calendar-month arithmetic with month-end clamping, the days-left
calculation on the analysis day, the capability ratio, the pathlength
deviation fraction, the blank fraction, the per-kind field validation,
the policy merge and the cleared/watch/blocked verdicts are exercised by
the gate 3 contract test: scripts/test_q7005_equipment_control.py
against scripts/q7005_equipment_control_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7005_equipment_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
