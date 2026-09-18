---
name: e2007-discharge-injection-probe-calibration
description: "Verify the calibration arrangement an injection probe must be set up in before discharge pulses are driven into a harness, per ECSS-E-ST-20-07C clause 5.4.13.3: compare both fixture terminations against the reflection a reference conductor tolerates, reduce the recorded calibration pulses to a mean current and a repeatability spread, derive the probe injection loss from the drive applied and the current the fixture carried, invert it into the generator setting the target calibration current needs, and confirm that setting, the monitor bandwidth and the fixture validity window all still hold. Use when a probe injection bench is calibrated or its records reviewed. Trigger: ecss, e-st-20-07c, discharge-injection-probe-calibration, injection-probe-calibration-fixture, probe-injection-loss, calibration-pulse-repeatability, calibration-fixture-termination-match, injection-drive-setting."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-discharge-injection-probe-calibration, injection-probe-calibration-fixture, probe-injection-loss, calibration-pulse-repeatability, calibration-fixture-termination-match, injection-drive-setting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Discharge Injection-Probe Calibration (space-systems/ecss/e2007-discharge-injection-probe-calibration)

Use when the task is the calibration arrangement of ECSS-E-ST-20-07C
clause 5.4.13.3 -- the fixture and the measurement that are set up
before the injection probe is clamped onto a flight harness, so that the
drive dialled into the generator is known to produce the discharge
current the test plan asks for.

## Domain quick reference

- The calibration happens on a fixture, not on the harness. A harness is
  an unknown impedance with branches on it, so the current a given drive
  produces there is not predictable in advance. The fixture replaces it
  with a through conductor of a stated characteristic impedance, and
  that known line is what makes the drive-to-current relation a number
  instead of a guess.
- The fixture is only a reference while both ends are terminated. An
  unterminated or badly terminated end reflects the pulse back along the
  conductor, and the monitor then reads an incident pulse summed with
  its own echo. Both terminations are graded by the fraction of the
  incident wave they return, and the budget is small because the error
  lands directly on the calibration constant.
- One shot is not a calibration. The quantity the arrangement has to
  establish is repeatable, so a run of pulses is recorded and reduced to
  a mean and a spread; a spread wider than the arrangement's own
  tolerance means the number carries the fixture's variability, not the
  probe's transfer.
- The probe is characterized as a loss, and a loss inverts. Applying a
  drive and reading the resulting fixture current gives the injection
  loss in dB; that same figure run backwards gives the drive needed for
  any other target current, which is what the harness injection will
  actually be set to.
- A derived setting is not automatically an available setting. It has to
  sit inside the generator range with room left, and the monitor that
  read the calibration current has to be fast enough for the pulse edge,
  or the calibrated current is the digitizer's version of it.
- Calibration has an age. A fixture whose own calibration window has
  closed provides no traceable reference, and one about to close will
  not survive a long injection campaign.

## Workflow

1. Validate the fixture: a positive characteristic impedance and both
   terminations present, each converted to a reflection magnitude and
   compared with the arrangement's budget.
2. Reduce the recorded calibration pulses to a count, a mean current,
   the extremes and the relative spread, refusing a run too short to
   support a repeatability statement.
3. Compare the spread with the tolerance the arrangement has to hold.
4. Derive the probe injection loss in dB from the drive applied at the
   probe and the equivalent voltage the mean fixture current represents
   on the fixture conductor.
5. Invert that loss to obtain the generator drive that produces the
   target calibration current on the same fixture.
6. Confirm the derived setting is inside the generator range, absorbing
   an exact equality at the limit with a relative tolerance rather than
   by widening the range.
7. Derive the monitor bandwidth the pulse edge demands and compare it
   with the bandwidth declared for the monitor used.
8. Compute the validity left on the fixture calibration, then separate
   findings from limitations and return the setting the harness
   injection will use.

## Pitfalls

- Calibrating on the harness itself. Its impedance is neither known nor
  constant along its length, so the drive-to-current relation it gives
  belongs to that one clamp position.
- Leaving one end of the fixture conductor open. The reflection arrives
  back inside the pulse and inflates the current the monitor reports,
  which under-sets every later drive.
- Taking a single shot as the calibration constant. Without a spread
  there is no statement about what the next pulse will do.
- Reading the injection loss as a fixed property of the probe. It is the
  probe on this fixture at this impedance; a different fixture impedance
  gives a different number for the same probe.
- Dialling a derived setting that sits at the top of the generator
  range. It works on the calibration day and has nothing left when the
  target current is raised or the cable run grows.
- Trusting a fixture whose own calibration has lapsed. Every current in
  the campaign then traces to nothing.

## Behavior contract (gate 3)

The fixture validation and termination reflections, calibration-pulse
statistics and repeatability test, probe injection-loss derivation,
drive-setting inversion, generator-range check, monitor-bandwidth
comparison, calibration-validity computation and the arrangement verdict
are exercised by the gate 3 contract test:
scripts/test_e2007_discharge_injection_probe_calibration.py against
scripts/e2007_discharge_injection_probe_calibration_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_discharge_injection_probe_calibration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
