---
name: e2007-measurement-device-calibration-interval
description: "Verify that every antenna, probe and sensor of an electromagnetic-compatibility measurement chain still holds a valid calibration, anchored at ECSS-E-ST-20-07C clause 5.2.11.1: take the last calibration date of each device, add the biennial recalibration interval honouring month lengths, pull the result forward to any damage the device suffered since, and keep the earlier of the two as the real due date; then hold that date against the planned measurement window so a device lapsing mid-campaign is caught before the run. Use when planning, auditing or accepting an emission or susceptibility campaign. Trigger: ecss, e-st-20-07c, measurement-device-calibration-interval, biennial-recalibration-interval, antenna-calibration-currency, probe-recalibration-due-date, sensor-damage-invalidation, emc-campaign-calibration-audit."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-measurement-device-calibration-interval, biennial-recalibration-interval, antenna-calibration-currency, probe-recalibration-due-date, sensor-damage-invalidation, emc-campaign-calibration-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Measurement Device Calibration Interval (space-systems/ecss/e2007-measurement-device-calibration-interval)

Use when the task is the recalibration rule of ECSS-E-ST-20-07C clause
5.2.11.1 -- the devices that sense the field or the current during a
compatibility measurement carry a calibration that expires on a two-year
cadence, and expires early whenever the device has been damaged.

## Domain quick reference

- Three device families are governed: the antennas that receive the
  radiated field, the probes that sense a conducted current or a local
  field, and the sensors that report the quantities the measurement is
  reduced against. A spectrum analyser, a cable or a fixture is graded
  by a different rule and does not belong in this inventory.
- The ordinary end of validity is the interval anniversary of the last
  calibration. Two years is the ceiling, not the target: a laboratory
  may impose a shorter cadence, and that shorter cadence then governs.
  An interval declared longer than the ceiling is not a finding to be
  reported, it is an invalid policy and the input is refused.
- Month arithmetic has to honour month lengths. A device calibrated on
  a leap day has no anniversary two years later, and a calibration on
  the last day of a long month must not roll into the following month;
  both clamp to the end of the target month.
- Damage overrides the interval. A dropped horn, an overloaded probe or
  a sensor exposed beyond its rating stops being trustworthy on the day
  it happened, not on its anniversary, so the last usable date is the
  day before the earliest damage recorded on or after the calibration.
  Damage before that calibration is superseded by it.
- Currency is judged twice: against the day the question is asked, and
  against the end of the declared measurement window. A device that is
  current today but falls due part way through the campaign cannot
  carry the campaign, and saying so afterwards invalidates the run.
- A due date reached exactly is still met. The device may be used on
  its due date; the day after is the first day it may not.

## Workflow

1. Normalize each device record: identifier, device family, last
   calibration date, the dates of any damage, and an optional house
   interval. Reject an unknown key, a blank identifier, a device family
   outside the governed three, a timestamp where a calendar date
   belongs, and an interval looser than the two-year ceiling.
2. Compute the interval end of validity by shifting the last
   calibration by the interval and clamping to the length of the target
   month.
3. Reduce the damage history to the earliest event on or after the last
   calibration; that event ends validity the day before it happened.
   Refuse a damage date later than the date the question is asked.
4. Keep the earlier of the two dates and record which of them drove it,
   so a report distinguishes an ordinary lapse from a damaged device.
5. Grade the device: past due, damage-invalidated, due inside the
   declared window, or current, with the days remaining.
6. Order the inventory by due date, refuse a duplicated identifier, and
   report the conforming fraction, the next device to fall due and one
   finding per device that cannot cover the window.

## Pitfalls

- Reading the two-year cadence as the interval to schedule against
  rather than the longest one permitted; a tighter house cadence
  governs wherever it is declared.
- Adding twenty-four months by arithmetic on the month number alone,
  which produces a 29 February that does not exist and silently shifts
  the due date into March.
- Letting the anniversary outlive a damage event. A device damaged
  inside its interval is not usable until it is recalibrated, whatever
  its certificate still says.
- Counting damage that happened before the last calibration: the
  recalibration answered it, and carrying it forward retires a device
  that is in fact current.
- Grading currency only on the day the campaign is planned. The date
  that matters is the end of the measurement window, and a device
  falling due inside it has to be recalibrated first.
- Treating a due date reached exactly as expired. The comparison is on
  the day after, and moving it a day early quietly shortens every
  interval in the laboratory.

## Behavior contract (gate 3)

The device normalization, month-clamped interval arithmetic, damage
reduction, effective-validity selection, device grading and inventory
aggregation are exercised by the gate 3 contract test:
scripts/test_e2007_measurement_device_calibration_interval.py against
scripts/e2007_measurement_device_calibration_interval_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_measurement_device_calibration_interval.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
