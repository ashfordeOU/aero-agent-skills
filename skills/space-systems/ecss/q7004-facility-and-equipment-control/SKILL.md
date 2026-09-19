---
name: q7004-facility-and-equipment-control
description: "Verify that the chamber, the fixture and the instrumentation of an ECSS thermal test are under control before the door closes. Use when the ECSS-Q-ST-70-04C quality clauses have to become a readiness statement: place each instrument in its calibration interval by day number, take the ratio of the tolerance the test must hold to the uncertainty measuring it, check the chamber reaches both extremes with margin rather than on equality, check the fixture is not massive enough to drive the item's own response, and require a controlling sensor plus a cross-check channel. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-test-facility-readiness, instrument-calibration-interval-standing, test-accuracy-ratio-check, thermal-chamber-envelope-margin, test-fixture-thermal-mass-ratio."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-facility-and-equipment-control, thermal-test-facility-readiness, instrument-calibration-interval-standing, test-accuracy-ratio-check, thermal-chamber-envelope-margin, test-fixture-thermal-mass-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Facility and Equipment Control (space-systems/ecss/q7004-facility-and-equipment-control)

Use when the task is the quality assurance side of ECSS-Q-ST-70-04C: whether
the chamber, the fixturing and the measuring equipment are under enough
control for the result to mean anything, answered before the test rather
than argued about after it.

## Domain quick reference

- Three things have to be in control and each fails differently. The
  instrumentation fails quietly, the facility fails at the edges, and the
  fixture fails by working too well.
- A sensor inside its calibration interval can still be the wrong sensor.
  What governs is the ratio between the tolerance the test has to hold and
  the uncertainty the instrument brings; below the house minimum the
  measurement is arguing with itself.
- Calibration standing is three states, not two. Valid, due soon and
  expired: a due-soon instrument is usable on day one of a campaign and
  expired by the end of it, which is why it is checked against the campaign
  end rather than the start.
- Chamber capability is checked with margin, never on equality. A chamber
  that only just reaches the required extreme has nothing left for the
  overshoot it takes to hold there, and the profile quietly clips.
- A fixture heavy against the item drives the item's thermal response. The
  profile that gets run is then the fixture's, and the item never sees the
  transition rate the test was written around.
- One temperature channel is an assertion. A second channel is what makes
  the first one evidence, and a setup with no declared controlling sensor
  has not said where the profile is held at all.

## Workflow

1. Take the test day as a day number and place each instrument in its
   calibration interval; refuse a record that predates its own calibration.
2. Compute each instrument's accuracy ratio from the required tolerance and
   its uncertainty, and compare it against the house minimum with the
   boundary absorbed.
3. Check the chamber envelope at both ends separately, against the policy
   margin, and name whichever end is short.
4. Take the fixture-to-item mass ratio and the attachment conformance
   together; either one alone can invalidate the run.
5. Count the temperature channels and confirm a controlling sensor exists
   before declaring anything ready.
6. Return ready only when every instrument is usable, the envelope holds,
   the fixture is passive and the channels are there — with the findings
   and the traceability duties attached.

## Pitfalls

- Treating a valid calibration sticker as sufficient. Interval standing and
  measurement adequacy are different questions and a sensor can pass one
  while failing the other.
- Checking the due date against the first day of the campaign. A six-week
  run started thirty days before the due day ends out of calibration, and
  the last results are the ones nobody can defend.
- Comparing a computed accuracy ratio against the minimum by bare
  arithmetic. A ratio built to land on the minimum can fall either side of
  it in the last place; the comparison has to absorb that, not the minimum.
- Accepting a chamber that reaches the extreme exactly. The margin is there
  for the overshoot, and without it the dwell starts late every cycle.
- Ignoring fixture mass because the fixture is not the test article. It is
  the thermal path into the test article, and a heavy one replaces the
  profile.
- Running a single channel because the chamber controller also logs. The
  controller reports its own set point, not the item, and there is nothing
  to check it against.

## Behavior contract (gate 3)

Calibration standing by day number, the accuracy ratio and its boundary,
the two-ended envelope margin check, fixture mass ratio and attachment
conformance, channel and controlling-sensor coverage and the overall ready
or not-ready verdict are exercised by the gate 3 contract test:
scripts/test_q7004_facility_and_equipment_control.py against
scripts/q7004_facility_and_equipment_control_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_q7004_facility_and_equipment_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
