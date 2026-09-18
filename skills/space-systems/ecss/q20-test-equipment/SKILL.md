---
name: q20-test-equipment
description: "Verify that the equipment a test is about to be run with satisfies the quality assurance control ECSS-Q-ST-20 clause 5.6.2 places on it, electrical ground support equipment included. Use when a test readiness review or a set-up check falls due: judge calibration at the day of use rather than the day of the audit, refuse a due day contradicting the calibration interval, weigh the uncertainty carried against the tolerance being judged as an accuracy ratio, keep a guard band at each end of the instrument span, refuse an unapproved change to the build standard, and hold equipment whose self-test or functional check has gone stale. Trigger: ecss, q-st-20-clause-5-6-2, test-equipment-calibration-validity-at-use, test-equipment-accuracy-ratio, egse-configuration-control, test-equipment-readiness-window."
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
  tags: [ecss, q-st-20-quality-assurance-scope, q20-test-equipment, q-st-20-clause-5-6-2, test-equipment-calibration-validity-at-use, test-equipment-accuracy-ratio, egse-configuration-control, test-equipment-readiness-window, test-equipment-range-guard-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance — Test Equipment Control (space-systems/ecss/q20-test-equipment)

Use when the task is clause 5.6.2 of ECSS-Q-ST-20: a test is about to be
run, and the equipment it will be run with has to be shown calibrated,
under configuration control, ready and suitable for the measurement —
electrical ground support equipment as much as the instruments.

## Domain quick reference

- Calibration is judged at the day of use, not the day of the audit. An
  instrument in date this morning and out of date on the test day is out
  of date, and a due day that contradicts the calibration day plus the
  interval is an input error rather than a finding.
- Being in calibration is not the same as being good enough. The
  uncertainty the equipment carries has to be small against the
  tolerance the measurement is judged on, and that ratio is what
  separates a usable reading from one that cannot decide the pass.
- Suitability is a range question as well as an accuracy one. A
  measurand sitting at the very end of an instrument's span is measured
  where the instrument is least trustworthy, so a guard band is kept
  clear at each end and the measurand has to sit inside what is left.
- Electrical ground support equipment is test equipment. It stimulates
  and it measures, its build standard changes between campaigns, and an
  unapproved change to it is an uncontrolled change to the test itself.
- Ready is a state with a date on it. A passed self-test and a
  functional check inside its window are what make equipment ready now,
  rather than ready the last time anybody looked.
- A calibration about to expire is a scheduling risk, not a refusal. It
  is carried as an advisory, because a slipped test date is what turns
  it into one.

## Workflow

1. Validate the release policy first: the accuracy ratio demanded, the
   margin at which an expiring calibration is flagged, the functional
   check window, whether a self-test is required, and the guard band.
   A ratio below one, or a guard band swallowing the span, is refused
   rather than used.
2. Validate the equipment record: a recognised kind, a span whose top
   sits above its bottom, a measurand that is not inverted, a positive
   uncertainty and tolerance, and a positive calibration interval.
3. Take the calibration due day, declared or derived, and the margin
   against the day of use. No record at all, or a negative margin,
   closes the assessment.
4. Test the configuration control: a named baseline and nothing
   unapproved outstanding against it.
5. Take the accuracy ratio as the tolerance over the uncertainty, and
   compare it with the policy.
6. Take the guard band as a share of the span and test whether the
   measurand sits inside what remains.
7. Take the readiness gaps: the self-test, and the age of the functional
   check against its window.
8. Close on one verdict in order: equipment not identified, calibration
   not valid, configuration not controlled, measurement capability
   insufficient, range not suitable, equipment not ready, or released
   for test. Across a set-up, report every item held back and why.

## Pitfalls

- Reading the calibration label on the day of the review. The test day
  is the one that matters, and a long set-up can cross the due date
  between the two.
- Accepting a calibrated instrument without weighing its uncertainty. In
  calibration and unable to decide the tolerance are entirely
  compatible, and the ratio is what shows it.
- Using an instrument at the end of its span. The reading is admissible
  and least trustworthy exactly where the guard band was meant to be.
- Leaving the electrical ground support equipment out of the control.
  Its build standard moves between campaigns, and an unapproved change
  there is an unapproved change to the test.
- Treating a passed self-test from last month as readiness. It is a
  record of that day; the window is what makes it a statement about
  this one.

## Behavior contract (gate 3)

The policy validation, equipment validation, the derived and declared
calibration due day, the margin at the day of use, the accuracy ratio
and its sufficiency, the range span, guard band and suitability, the
configuration control test, the readiness gaps, the release verdict and
the set-up level hold list are exercised by the gate 3 contract test:
scripts/test_q20_test_equipment.py against
scripts/q20_test_equipment_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_test_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
