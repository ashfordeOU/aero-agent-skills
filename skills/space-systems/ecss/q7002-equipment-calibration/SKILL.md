---
name: q7002-equipment-calibration
description: "Audit the instrument set an outgassing screening run depends on. Use when the microbalance, the thermocouples and the pressure gauge have to be cleared under ECSS-Q-ST-70-02C before a run starts: walk each calibration forward by whole calendar months so a month end lands where the calendar puts it, report the days left on the run day, compare the tolerance each instrument polices against the uncertainty it carries, refuse a balance division too coarse for the mass change being sought, and combine independent contributions in quadrature. Trigger: ecss, q-st-70-02c, outgassing-instrument-calibration, outgassing-microbalance-readability, outgassing-thermocouple-uncertainty-ratio, outgassing-calibration-due-day, outgassing-measurement-uncertainty-budget, outgassing-pressure-gauge-calibration."
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
  tags: [ecss, q-st-70-02-outgassing-scope, q7002-equipment-calibration, outgassing-microbalance-readability, outgassing-thermocouple-uncertainty-ratio, outgassing-calibration-due-day, outgassing-measurement-uncertainty-budget, outgassing-pressure-gauge-calibration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening -- Instrument Calibration (space-systems/ecss/q7002-equipment-calibration)

Use when the task is the instrument-accuracy step of a thermal-vacuum
outgassing screening under ECSS-Q-ST-70-02C: the microbalance, the specimen
and collector thermocouples and the pressure gauge are about to be used for a
run, and the question is whether their calibration state and their accuracy
support the numbers the run will report.

## Domain quick reference

- A calibration interval is counted in calendar months, not in days. Adding
  twelve months to the last day of a long month lands on the last day of the
  month it reaches, and a leap year moves the end of February with it.
- Whether an instrument is current is a question about the run day, not about
  today. A certificate that expires during a long soak was already short on
  the day the run started, and the days left is the number to report.
- Fitness is a ratio. An instrument is capable when the tolerance it polices
  is several times larger than the uncertainty it carries; the uncertainty on
  its own says nothing without the tolerance beside it.
- Resolution is separate from accuracy. A balance can hold a blameless
  certificate and still be unable to see the mass change being looked for,
  because its smallest division is a large share of that change.
- Independent contributions combine in quadrature, so a chain of small terms
  is smaller than their arithmetic sum, and the combined figure -- not the
  largest single term -- is what the tolerance is graded against.

## Workflow

1. Parse each calibration day, refusing a day the calendar does not have
   rather than rolling it into the next month.
2. Add the interval in whole months, falling the day back to the end of a
   shorter month, and take the result as the day the calibration runs out.
3. Take whole days from the run day to the due day, reporting an expired
   instrument and one inside the warning window as different findings.
4. Form the tolerance-to-uncertainty ratio for every instrument and raise a
   finding for each one below the required floor, naming the instrument.
5. Compare the balance division with the mass change divided by the required
   factor, absorbing an exact equality at the limit as representation error.
6. Combine the declared contributions in quadrature when a budget is given,
   grade the combined figure against its own tolerance by the same ratio, and
   report the set usable only when nothing above was raised.

## Pitfalls

- Adding 365 days for a year. The due day follows the calendar, and the
  difference shows up exactly at the month ends where certificates cluster.
- Checking the calibration on the day the question is asked. The run day is
  what governs, and a long soak can start current and finish expired.
- Reading a small uncertainty as capability. A tenth of a kelvin is excellent
  against a one-kelvin band and useless against a tenth-kelvin one.
- Confusing readability with accuracy. The division sets what the balance can
  see at all; the certificate sets how true what it sees is.
- Adding uncertainty contributions arithmetically. Quadrature is what
  independence buys, and summing instead quietly over-states the budget until
  someone relaxes a real limit to make it fit.

## Behavior contract (gate 3)

The day parsing, whole-month due-day arithmetic, days-remaining currency
findings, tolerance-to-uncertainty ratios, balance readability check and the
quadrature budget are exercised by the gate 3 contract test:
scripts/test_q7002_equipment_calibration.py against
scripts/q7002_equipment_calibration_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_equipment_calibration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
