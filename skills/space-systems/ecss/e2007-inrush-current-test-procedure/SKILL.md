---
name: e2007-inrush-current-test-procedure
description: "Plan the stabilisation, chain-check and switching steps a switch-on surge run follows, under ECSS-E-ST-20-07C clause 5.4.4.4. Use when an inrush-current procedure is written or reviewed: confirm the unit dwelled long enough to draw a steady current, group the optional measurement-chain check as passed, out of tolerance or omitted, derive the off-time each repeat needs for the input filter to discharge, order the arm, switch, record and recover steps so no leading edge is lost, assess the trigger against the noise floor and the expected peak, size the pre-trigger and record window, and return the step plan with its findings. Trigger: ecss, e-st-20-07c, inrush-current-test-procedure, switch-on-surge-capture-sequence, inrush-stabilisation-dwell, inrush-filter-discharge-off-time, inrush-capture-trigger-level, inrush-repeat-count."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-inrush-current-test-procedure, switch-on-surge-capture-sequence, inrush-stabilisation-dwell, inrush-filter-discharge-off-time, inrush-capture-trigger-level, inrush-repeat-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Inrush-Current Test Procedure (space-systems/ecss/e2007-inrush-current-test-procedure)

Use when the task is the procedure clause of ECSS-E-ST-20-07C clause
5.4.4.4 -- running the switch-on surge measurement itself: letting the
unit settle, optionally checking the measurement chain, and then arming,
switching and capturing the current transient often enough for the peak
to mean something.

## Domain quick reference

- The order of the steps is the measurement. A capture armed after the
  switching command misses the leading edge, and the leading edge is the
  part of the trace the clause exists for; the peak that survives in
  such a record is whatever the trace happened to open on.
- Stabilisation comes first because the surge is measured against the
  steady draw that follows it. A unit still warming up has a quiescent
  current that moves under the measurement, so the settled value the
  transient decays to is not yet the unit's own.
- Repeats need the filter discharged, not just the unit off. The surge
  is the input filter charging, so a repeat started before the filter
  has bled down draws a smaller peak and the run quietly reports the
  second-best number. The off-time follows from the filter time
  constant, and a few time constants remain as residual charge even when
  the rule is satisfied.
- The measurement-chain check is optional, and that has consequences
  rather than none. Skipping it leaves the amplitudes resting on the
  calibration record alone, which is a limitation carried with the
  results; running it and finding it outside tolerance is a finding
  against the run.
- A trigger level is bounded on both sides. Too close to the noise floor
  and the capture arms before anything was switched; too high up the
  expected peak and the record starts partway up the edge. The usable
  window is set by the noise floor and the peak together, never by one
  alone.
- Pre-trigger is part of the record length, not an extra. The window has
  to hold the quiescent draw before the switching instant plus the whole
  transient, so sizing the record from the transient alone always comes
  up short.

## Workflow

1. Validate the procedure: dwells and windows non-negative, the time
   constant, trigger level, noise floor and expected peak positive, the
   repeat count a whole number of events, and the noise floor below the
   expected peak.
2. Compare the achieved dwell against the dwell the unit needs to reach
   a steady draw.
3. Group the optional measurement-chain check as passed, out of
   tolerance, or omitted.
4. Derive the off-time from the filter time constant and the discharge
   multiple, compare it with the off-time used, and compute the charge
   still on the filter at the next switch-on.
5. Assess the trigger level against the noise floor and the expected
   peak, and the pre-trigger and record length against the transient.
6. Build the ordered step plan -- stabilise, optional chain check, then
   arm, switch on, record, switch off and recover per event -- stretching
   a short off-time to the derived minimum.
7. Aggregate: a short dwell, late arming, an unrecovered filter, too few
   repeats, an out-of-tolerance check, an unusable trigger or an
   undersized window are findings; an omitted check and residual filter
   charge are limitations.

## Pitfalls

- Arming the capture and switching in the same breath. The command has
  to reach an already-armed record, or the first microseconds are gone.
- Repeating the switch-on as fast as the operator can reach the switch.
  The filter, not the operator, sets the minimum gap between repeats.
- Reading the optional chain check as "not required, so it changes
  nothing". It changes what the amplitudes rest on, and that belongs in
  the report.
- Setting the trigger just under the expected peak to avoid false arms.
  That trades a false arm for a truncated edge, and the edge cannot be
  recovered afterwards.
- Sizing the record on the transient alone. Pre-trigger has to fit
  inside the same window, and without it there is nothing to measure the
  surge against.

## Behavior contract (gate 3)

The procedure validation, stabilisation comparison, chain-check
grouping, recovery derivation and residual charge, trigger-level and
capture-window checks, the ordered step plan and the aggregate verdict
are exercised by the gate 3 contract test:
scripts/test_e2007_inrush_current_test_procedure.py against
scripts/e2007_inrush_current_test_procedure_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_inrush_current_test_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
