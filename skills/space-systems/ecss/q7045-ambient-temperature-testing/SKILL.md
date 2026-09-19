---
name: q7045-ambient-temperature-testing
description: "Verify that a room-temperature mechanical test on a metallic piece was run at the rates and with the instrumentation ECSS-Q-ST-70-45C expects: convert the commanded crosshead speed into the strain rate and the elastic stress rate the piece actually saw, grade each against the window that applies to the property being measured, confirm the load cell was working inside its usable span and its calibration validity, and confirm the extensometer class and gauge length suit a proof-strength or an elongation reading. Use when reviewing a tensile report, setting up a machine or explaining a strength figure that came out high. Trigger: ecss, q-st-70-45c, ambient-tensile-test-rate, crosshead-speed-to-strain-rate, load-cell-usable-span, extensometer-class-selection, proof-strength-measurement."
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
  tags: [ecss, q-st-70-45c-metallic-mechanical-testing, q-st-70-45c, q7045-ambient-temperature-testing, ambient-tensile-test-rate, crosshead-speed-to-strain-rate, load-cell-usable-span, extensometer-class-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Ambient Temperature Testing (space-systems/ecss/q7045-ambient-temperature-testing)

Use when the task is the room-temperature part of the test-conditions clause
of ECSS-Q-ST-70-45C: the loading rate the machine has to apply, the span the
load cell has to be working in, and the extensometer the strain has to be read
with.

## Domain quick reference

- The machine is commanded in crosshead speed and the requirement is in strain
  rate. The conversion runs through the parallel length, so the same speed is
  a different rate on a short piece and a long one, and a speed copied between
  drawings silently changes the test.
- Rate is not one window. The elastic part of the curve is controlled in
  stress rate, and the plastic part in strain rate; a rate that is legal for
  measuring a proof strength can be well outside the window for measuring the
  strength after yielding.
- Metals are rate sensitive, upward. Pulling faster raises the measured
  strength, so an unnoticed rate excess produces a number that looks good and
  is not the material's. That is why the high-rate case matters more than the
  low-rate one.
- A load cell is not linear and trustworthy across its whole nameplate. The
  lower part of the range carries the cell's own uncertainty as a large
  fraction of the reading, so a peak load down near the bottom of the range
  needs a smaller cell, not a careful operator.
- The calibration is part of the instrument. A cell within its usable span but
  past its calibration date has an unknown span, and a test run on it is not a
  measurement.
- Extensometer class is chosen by what is being read, not by what is
  available. A proof strength is a small-offset measurement and needs the
  tighter class; an elongation after fracture is a large displacement and does
  not.
- The extensometer gauge length has to be the gauge length the result is
  reported on. A device set to a convenient length reports strain over that
  length, and an elongation quoted against a different one is not comparable.

## Workflow

1. Validate the piece geometry and the commanded crosshead speed, and convert
   the speed into a strain rate over the parallel length.
2. Convert the strain rate into the elastic stress rate through the material's
   modulus, so the elastic-region requirement can be graded in its own units.
3. Grade the stress rate against the elastic window and the strain rate
   against the plastic window, keeping the two verdicts separate.
4. Compute the peak load the piece will reach from its section and expected
   strength, and express it as a fraction of the load cell's range.
5. Reject a peak below the cell's usable lower fraction as an instrument
   choice, not a measurement nuisance, and check the calibration is current at
   the test date.
6. Choose the extensometer class from the quantity being measured, and check
   that the device gauge length matches the reported gauge length.
7. Close with a verdict naming every rate, instrument-span, calibration and
   extensometer finding that bears on whether the numbers are attributable.

## Pitfalls

- Copying a crosshead speed between test pieces. The strain rate depends on
  the parallel length, so the same speed on a shorter piece is a faster test.
- Grading one rate for the whole curve. The elastic and plastic windows are
  different requirements, and satisfying the one the operator remembered says
  nothing about the other.
- Treating a rate excess as conservative. It is not; it inflates the measured
  strength, and the inflated number is the one that goes into the allowable.
- Using a large load cell for a small piece. A peak load at a few percent of
  the cell range buries the result inside the cell's own uncertainty, and no
  amount of averaging recovers it.
- Reading a calibration sticker as a calibration. The date has to cover the
  test date; an expired cell has an unknown span whatever its usable fraction.
- Quoting elongation from an extensometer set to a different gauge length than
  the one reported, or reading a proof strength on a looser-class device
  because it was the one already fitted.

## Behavior contract (gate 3)

The crosshead-to-strain-rate conversion, the elastic stress-rate derivation,
the separate elastic and plastic rate windows, the peak-load and usable-span
computation, the calibration-validity check and the extensometer class and
gauge-length rules are exercised by the gate 3 contract test:
scripts/test_q7045_ambient_temperature_testing.py against
scripts/q7045_ambient_temperature_testing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_ambient_temperature_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
