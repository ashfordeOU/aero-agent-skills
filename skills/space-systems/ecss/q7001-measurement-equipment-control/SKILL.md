---
name: q7001-measurement-equipment-control
description: "Audit the instruments a cleanliness verification campaign will lean on before it starts. Use when balances, particle counters and spectrometers have to be cleared under ECSS-Q-ST-70-01C: walk each certificate forward by whole calendar months so a month end lands where the calendar puts it, report the days left on the measurement date, compare each detection floor against the tightest value it polices through a sensitivity ratio, combine independent contributions in quadrature against the tolerance policed, grade a counter sizing error against its smallest bin, and block an untraceable instrument outright. Trigger: ecss, q-st-70-01c, cleanliness-instrument-calibration-currency, cleanliness-detection-floor-sensitivity-ratio, particle-counter-sizing-error, cleanliness-measurement-uncertainty-budget, cleanliness-equipment-traceability, nvr-balance-readability-control."
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
  tags: [ecss, q-st-70-01-cleanliness-scope, q7001-measurement-equipment-control, cleanliness-instrument-calibration-currency, cleanliness-detection-floor-sensitivity-ratio, particle-counter-sizing-error, cleanliness-measurement-uncertainty-budget, cleanliness-equipment-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Measurement Equipment Control (space-systems/ecss/q7001-measurement-equipment-control)

Use when the task is the equipment-control step of cleanliness
verification under ECSS-Q-ST-70-01C: a set of balances, particle
counters, spectrometers and witness-plate readers is about to produce
verification evidence, and the question is whether their calibration
state and their sensitivity support the numbers that evidence will
carry.

## Domain quick reference

- A calibration interval is counted in calendar months. Walking twelve
  months from the last day of a long month lands on the last day of the
  month it reaches, and a leap year moves the end of February with it.
- Currency is a question about the measurement date, not about today. A
  certificate that runs out during the campaign was already short on the
  day the run was planned, and the days remaining is the number the plan
  needs.
- Sensitivity is a ratio, not a comparison. An instrument whose
  detection floor sits just under the value it polices produces readings
  indistinguishable from its own noise; it has to resolve that value
  several times over.
- The floor is a property of the setup, not of the instrument alone.
  Rinsed area, aliquot fraction and recovery all divide into it, so the
  same balance carries a different floor on each surface it serves.
- Independent contributions combine in quadrature. Summing them
  arithmetically inflates the budget and can block a capable
  instrument; the tolerance policed then has to stand several times
  clear of that combined figure.
- A particle counter's sizing error moves counts between bins. An error
  comparable with the width of the smallest bin reported changes the
  distribution without changing the total, which is invisible in the
  count.
- Traceability is binary. An instrument without a chain back to a
  reference produces numbers that cannot support a verification claim,
  however good its repeatability looks.

## Workflow

1. Validate each instrument record: identifier, last calibration date,
   interval in whole months, the value it polices, the detection floor
   it achieves in service.
2. Walk the certificate forward by calendar months, clamping a day that
   does not exist in the month it lands in, and report the status and
   days remaining at the measurement date.
3. Form the sensitivity ratio of the policed value to the detection
   floor and compare it with the minimum, absorbing an exact landing on
   the minimum with a named relative tolerance.
4. Where an uncertainty budget is declared, combine the contributions
   in quadrature and form the ratio of the tolerance policed to the
   combined uncertainty.
5. Where a counter is in the set, grade its sizing error against the
   smallest bin it reports.
6. Block an instrument with no traceable calibration chain regardless
   of every other number.
7. Summarise the set into per-instrument entries, blocked identifiers,
   the usable fraction and the pooled findings.

## Pitfalls

- Adding a calibration interval as three hundred and sixty five days.
  A month-end certificate then lands a day out, and the instrument is
  used one day past its cover.
- Reading currency on the day the question is asked. The campaign runs
  later, and an instrument in date today can be overdue on the run day.
- Accepting a detection floor just below the policed value. The
  readings near that value are the instrument talking about itself, and
  the acceptance decision inherits the noise.
- Quoting a detection floor from the datasheet. The floor in service
  carries the sampled area, the aliquot and the recovery, and is
  coarser than the bench figure by all three.
- Summing uncertainty contributions arithmetically. The budget inflates,
  a capable instrument is blocked, and the fix usually applied is to
  drop a contribution rather than to combine them correctly.
- Treating a counter's total count as unaffected by sizing error. The
  total survives; the distribution the requirement is written against
  does not.

## Behavior contract (gate 3)

The calendar-month interval walk, day clamping, currency status,
sensitivity ratio, quadrature uncertainty budget,
tolerance-to-uncertainty ratio, counter sizing-error grading,
traceability block and the set summary are exercised by the gate 3
contract test:
scripts/test_q7001_measurement_equipment_control.py against
scripts/q7001_measurement_equipment_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_measurement_equipment_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
