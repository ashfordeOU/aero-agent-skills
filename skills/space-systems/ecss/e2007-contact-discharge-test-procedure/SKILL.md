---
name: e2007-contact-discharge-test-procedure
description: "Plan the waveform calibration and the application steps a direct contact discharge run follows, under ECSS-E-ST-20-07C clause 5.4.14.4. Use when the run is written or reviewed: derive the nominal first peak, the thirty and sixty nanosecond currents and the rise time from each charge level, group the calibration as passed, out of tolerance or omitted, reject one older than its validity window, stretch a short interval to the one the generator recharge imposes, require enough discharges at each point, order stabilise, calibrate, apply and recover over ascending levels and both polarities, total the discharges and the bench time, and return the plan with its findings. Trigger: ecss, e-st-20-07c, contact-discharge-test-procedure, contact-discharge-waveform-calibration, esd-current-target-first-peak, contact-discharge-application-sequence, esd-generator-recharge-interval, contact-discharge-polarity-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-contact-discharge-test-procedure, contact-discharge-waveform-calibration, esd-current-target-first-peak, contact-discharge-application-sequence, esd-generator-recharge-interval, contact-discharge-polarity-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Contact Discharge Test Procedure (space-systems/ecss/e2007-contact-discharge-test-procedure)

Use when the task is the procedure clause of ECSS-E-ST-20-07C clause
5.4.14.4 -- proving the generator delivers the discharge current
waveform its severity level names, and then applying the discharges to
the unit through the tip in an order that makes the outcome readable.

## Domain quick reference

- The level is a charge voltage; the exposure is a current. Calibrating
  into the current target is what ties one to the other: the first peak
  and the two decay sample points are read off the target, and each of
  them scales linearly with the charge level, so the whole target is
  derived from the level rather than looked up run by run.
- The edge matters as much as the peak. An event with the right peak and
  a slow rise is a different spectrum, so it is not the event the level
  refers to, and an edge outside its band is a finding against the run
  rather than a note beside it.
- A calibration has an age. The generator drifts, its tip wears and its
  network ages, so a calibration older than its validity window has
  stopped describing the machine that delivered these discharges even
  though the paper is on file.
- An omitted calibration is not the same failure as a failed one. Nothing
  measured means every amplitude rests on the generator's own record,
  which is a limitation carried with the results; a measurement outside
  tolerance means the run delivered something other than what was asked
  for, which is a finding.
- The generator is not a source until it has settled. A high-voltage
  supply delivers a drifting charge voltage while it warms, so the
  events taken in the first minutes are at a level nobody can name
  afterwards -- and they are usually the low-level ones where an upset
  would have been most informative.
- The interval is the slowest of three things: what the procedure
  declared, how long the generator takes to recharge, and the floor
  below which consecutive events stop being separate events. A procedure
  declaring something faster is stretched to the slowest, not run as
  written.
- Levels ascend and both polarities are applied. Taking the unit to the
  top level first destroys the information the lower levels would have
  carried, and a single-polarity run covers half the exposure -- which
  half being unpredictable in advance.
- A handful of discharges at a point proves nothing. Contact discharge
  upset is probabilistic, so the absence of an upset only means
  something after enough events at that point, polarity and level, with
  somebody watching the unit while they are applied.

## Workflow

1. Validate the run: non-negative dwells, a positive declared interval
   and recharge time, a whole number of discharges per point, unique
   point labels, recognized polarities and strictly ascending levels.
2. Derive the nominal current target at the calibration level from the
   amperes-per-kilovolt coefficients, defaulting them only when the
   campaign declares none.
3. Group the calibration as passed, out of tolerance or omitted from the
   fractional deviation of each reading, the rise time against its band
   and the age against the validity window.
4. Compare the achieved dwell against the dwell the generator needs to
   settle.
5. Derive the effective interval as the slowest of the declared one, the
   recharge time and the floor, and record whether the declared one had
   to be stretched.
6. Check the discharges per point against the minimum and confirm the
   unit is watched through the application steps.
7. Build the ordered plan -- stabilise, calibrate when it was run, then
   apply at each point for each polarity at each ascending level, then
   recover -- and total the discharges and the bench time they occupy at
   the effective interval.
8. Aggregate: a short dwell, an out-of-tolerance or expired calibration,
   an edge outside its band, a stretched interval, too few discharges
   and an unwatched unit are findings; an omitted calibration and a
   single polarity are limitations.

## Pitfalls

- Reading the calibration as paperwork. It is what every amplitude in
  the report rests on, and skipping it changes the standing of each
  number rather than leaving a hole in a file.
- Checking the first peak and never the decay points or the edge. The
  peak alone does not make the event the one the level names.
- Treating a calibration certificate as timeless. The window is what
  makes it describe this generator on this day.
- Starting the sequence as soon as the generator powers up. The charge
  voltage is still moving and the level written in the log is not the
  level delivered.
- Setting the repetition from the operator's rhythm. The recharge time
  and the floor both govern, and the slowest of the three wins.
- Running the top level first to save bench time. It costs the
  information the lower levels would have carried.
- Taking two or three discharges at a point and recording no upset. At
  that count the absence of an upset is not evidence of anything.
- Applying the discharges with nobody watching the unit, then reading a
  clean log as a clean result.

## Behavior contract (gate 3)

The run validation, level and polarity ordering, nominal current-target
derivation, calibration grouping with its rise-time and validity checks,
stabilisation comparison, effective-interval derivation, discharge-count
and monitoring checks, the ordered step plan, the discharge and bench
time totals and the aggregate verdict are exercised by the gate 3
contract test:
scripts/test_e2007_contact_discharge_test_procedure.py against
scripts/e2007_contact_discharge_test_procedure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_contact_discharge_test_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
