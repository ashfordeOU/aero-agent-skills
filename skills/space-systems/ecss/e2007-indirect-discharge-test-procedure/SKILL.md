---
name: e2007-indirect-discharge-test-procedure
description: "Plan the stabilisation, fixture calibration and discharge application steps an indirect discharge exposure follows, under ECSS-E-ST-20-07C clause 5.4.12.4. Use when the run is written or reviewed: confirm the generator dwelled long enough to settle, group the fixture calibration as passed, out of tolerance or omitted from the first peak and the rise time, derive the interval the coupling plane bleed imposes and stretch a short one to it, require enough repeats at each point, order the stabilise, calibrate, expose and recover steps over ascending levels and both polarities, total the discharges and the bench time, and return the plan with its findings. Trigger: ecss, e-st-20-07c, indirect-discharge-test-procedure, esd-generator-stabilisation-dwell, indirect-discharge-fixture-calibration, indirect-discharge-application-sequence, esd-discharge-repetition-interval, indirect-discharge-polarity-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-indirect-discharge-test-procedure, esd-generator-stabilisation-dwell, indirect-discharge-fixture-calibration, indirect-discharge-application-sequence, esd-discharge-repetition-interval, indirect-discharge-polarity-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Indirect Discharge Test Procedure (space-systems/ecss/e2007-indirect-discharge-test-procedure)

Use when the task is the procedure clause of ECSS-E-ST-20-07C clause
5.4.12.4 -- running the indirect discharge exposure itself: letting the
generator settle, checking its output into the calibration fixture, and
then applying the discharges to the coupling plane in an order that
makes the result readable.

## Domain quick reference

- The generator is not a source until it has settled. A high-voltage
  supply delivers a drifting charge voltage while it warms, so the
  discharges taken in the first minutes are at a level nobody can name
  afterwards, and they are usually the ones taken at the lowest level
  where an upset would have been most informative.
- Calibration into the fixture is what ties a level to an event. The
  fixture reads the first peak and the rise time the generator actually
  delivers; without that reading the amplitudes rest on the generator's
  own record alone, which is a limitation that travels with the results
  rather than an omission with no consequence.
- The rise time is as much part of the exposure as the peak. An event
  with the right peak and the wrong edge has a different spectrum, so it
  is not the event the severity level refers to, and a reading outside
  the band is a finding against the run rather than a note.
- The repetition interval belongs to the coupling plane, not to the
  operator. The plane bleeds down through its resistor chain on an
  exponential, and an interval shorter than several of those time
  constants starts the next event on a plane that never came back to the
  reference. A procedure that declares a shorter interval has to be
  stretched to the derived one, not run as written.
- Levels ascend. Taking the unit to the top level first destroys the
  information the lower levels would have given, because an upset there
  no longer says which level first produced it.
- Both polarities are part of the exposure. A single-polarity run covers
  half of it, and the half it covers is not predictable in advance.
- A handful of discharges at a point proves nothing. An indirect
  discharge upset is probabilistic, so the absence of an upset only
  means something after enough events at that point, polarity and level.
- Watching the unit is a step, not a background activity. An upset that
  clears on its own between events leaves no trace unless somebody was
  observing when it happened.

## Workflow

1. Validate the run: non-negative dwells, a positive interval, plane
   time constant and target peak, whole numbers of points and repeats,
   a recognized calibration state with its readings when it was
   measured, ascending severity levels and recognized polarities.
2. Compare the achieved dwell against the dwell the generator needs to
   settle.
3. Group the fixture calibration as passed, out of tolerance or omitted
   from the first-peak deviation, and check the measured rise time
   against its band.
4. Derive the minimum interval from the plane time constant and the
   bleed multiple, compare it with the declared interval, and carry the
   larger of the two forward as the effective interval.
5. Check the repeats per point against the minimum and confirm the unit
   is watched through the application steps.
6. Build the ordered plan -- stabilise, calibrate when it is run, then
   expose at each point for each polarity at each ascending level, then
   recover -- and total the discharges and the bench time they take.
7. Aggregate: a short dwell, an out-of-tolerance calibration, an edge
   outside its band, too short an interval, too few repeats and an
   unwatched unit are findings; an omitted calibration and a single
   polarity are limitations.

## Pitfalls

- Starting the sequence as soon as the generator powers up. The charge
  voltage is still moving, and the level written in the log is not the
  level delivered.
- Reading the fixture calibration as optional paperwork. It is what the
  amplitudes rest on, and skipping it changes the standing of every
  number in the report.
- Checking the first peak and never the rise time. The peak alone does
  not make the event the one the level names.
- Setting the interval from the generator's recharge time. The coupling
  plane bleeds far more slowly, and the slower of the two governs.
- Running the top level first to save bench time. It costs the
  information the lower levels would have carried.
- Taking two or three discharges at a point and recording no upset. At
  that count the absence of an upset is not evidence of anything.
- Applying the discharges with nobody watching the unit, then reading a
  clean log as a clean result.

## Behavior contract (gate 3)

The procedure validation, level and polarity ordering, stabilisation
comparison, calibration grouping and rise-time check, bleed-derived
interval, repeat and monitoring checks, the ordered step plan, the
discharge totals and the aggregate verdict are exercised by the gate 3
contract test:
scripts/test_e2007_indirect_discharge_test_procedure.py against
scripts/e2007_indirect_discharge_test_procedure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_indirect_discharge_test_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
