---
name: calibration-control
description: "Use when you must control calibration of inspection, measuring, and test equipment under an AS9100-style QMS: determine the test accuracy ratio (TAR, 4:1 guidance) between the calibration standard and the unit under test, judge calibration due dates and overdue instruments, check a measured value against nominal and tolerance, and decide recall versus review when a calibrated standard drifts out of tolerance. Covers the calibration system (who calibrates, traceability to national standards), calibration intervals and due dates, out-of-tolerance handling, and calibration records with status labels. Produces the TAR verdict, the due-date verdict, the tolerance verdict, and the out-of-tolerance impact verdict that gate instrument use and product release. Trigger: calibration, TAR, test accuracy ratio, out of tolerance, calibration due, instrument recall, traceability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [calibration-control, calibration, tar, test-accuracy-ratio, out-of-tolerance, calibration-due, instrument-recall, traceability, as9100, metrology]
  version: 0.1.0
  author: Aero Agent Skills
---

# Calibration Control (manufacturing-quality/as9100/calibration-control)

Use when the task is calibration control for inspection, measuring, and
test equipment under an AS9100-style QMS: the calibration system (who
calibrates, traceability to national standards), calibration intervals
and due dates, test accuracy ratio, out-of-tolerance handling,
calibration records and status labels, and product recall when a
standard drifts.

## Domain quick reference

- AS9100 requires monitoring and measuring resources to be controlled
  and calibrated or verified at specified intervals, with traceability
  to national or international measurement standards (paraphrase of
  clause 7.1.5 practice). The organization decides who calibrates
  (internal metrology lab or accredited external provider) and keeps
  the traceability chain to the national standard.
- Test accuracy ratio (TAR): the standard's accuracy divided by the
  unit-under-test's accuracy. Both accuracies must use the same unit
  or the same fraction convention. TAR >= 4 is ok per the widely used
  4:1 guidance; below 4 the standard cannot adequately verify the unit.
- Calibration intervals: set from manufacturer guidance, use history,
  and drift data; the due date is the interval end. An instrument past
  its due date is overdue and must be withdrawn from service until
  recalibrated.
- Out of tolerance (OOT): when a check finds the standard drifted,
  evaluate the affected period (from the last good calibration to
  detection). Product released during that period with suspect
  equipment requires recall or containment; otherwise a record review
  suffices.
- Calibration records: equipment id, standard used, as-found and
  as-left data, due date, and status label (calibrated, due, overdue).
  Status labels prevent use of equipment whose calibration has lapsed.

## Workflow

1. Identify the equipment and the accuracy required for the unit under
   test (fraction or same unit).
2. Verify the standard used and its traceability to a national
   standard; check the TAR with tar_verdict().
3. Confirm the calibration interval and due date; check the due status
   with calibration_due_verdict().
4. Run the measurement; check against nominal and tolerance with
   tolerance_check().
5. If the standard drifts out of tolerance, determine the affected
   period and decide recall versus review with oot_impact_verdict().
6. Record as-found and as-left data, status label, and next due date;
   segregate equipment that is due or out of tolerance.

## Pitfalls

- Mixing units in the TAR: both accuracies must be the same unit or
  both fractions, or the ratio is meaningless.
- Using a standard with TAR below 4: the 4:1 guidance is a floor;
  below it the standard dominates the measurement uncertainty.
- Continuing to use an overdue instrument: withdraw and segregate it
  until recalibrated, and record the lapse.
- Checking tolerance without the standard's own accuracy: an
  in-tolerance reading from an inaccurate standard is not a valid pass.
- Releasing product without an OOT impact decision: any product
  verified during the affected period with a drifted standard needs
  recall or containment, not just a record note.

## Behavior contract (gate 3)

The calibration decision logic (TAR verdict, due-date verdict,
tolerance check, and out-of-tolerance impact verdict) is exercised by
the gate 3 contract test: scripts/test_calibration_control.py against
scripts/calibration_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_calibration_control.py

## Compliance

- Standards referenced, not reproduced: AS9100 text is proprietary
  (IAQG/SAE); this skill uses name and paraphrase only, per
  standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false; the standard is listed
  reference-only.
