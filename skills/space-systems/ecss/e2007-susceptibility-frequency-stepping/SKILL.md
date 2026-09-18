---
name: e2007-susceptibility-frequency-stepping
description: "Determine whether a susceptibility test steps across its whole declared frequency range, as ECSS-E-ST-20-07C clause 5.2.10.1 requires. Use when a radiated or conducted susceptibility scan is planned or graded: reject a continuously swept scan where stepped scanning is required, check the first and last steps reach the range ends, size every increment against the permitted fraction of its own lower frequency so no sub-band is left unstimulated, verify each dwell holds long enough for the unit to respond, build a compliant step plan, and total the scan duration. Trigger: ecss, e-st-20-07c, susceptibility-frequency-stepping, stepped-susceptibility-scan, susceptibility-step-size-fraction, susceptibility-dwell-time, susceptibility-range-coverage, continuous-sweep-rejection."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-susceptibility-frequency-stepping, stepped-susceptibility-scan, susceptibility-step-size-fraction, susceptibility-dwell-time, susceptibility-range-coverage, continuous-sweep-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Susceptibility Frequency Stepping (space-systems/ecss/e2007-susceptibility-frequency-stepping)

Use when the task is the frequency-stepping requirement of
ECSS-E-ST-20-07C clause 5.2.10.1 -- showing that a susceptibility test
covered its whole declared range, and covered it by stepping the
stimulus rather than sliding it continuously past the unit.

## Domain quick reference

- Emission and susceptibility scan for opposite reasons, and the
  clause reflects that. An emission run listens, so it can sweep. A
  susceptibility run drives the unit and then waits to see whether the
  unit misbehaves, so the stimulus has to sit still long enough for a
  response to appear. A continuous sweep never holds anywhere, and a
  slow-responding unit is disturbed at a frequency the scan has
  already left by the time the symptom shows.
- Step size is a fraction of the current frequency, not a fixed number
  of hertz. A 1 percent rule means 20 kHz steps at 2 MHz and 20 MHz
  steps at 2 GHz, which is what keeps the number of steps finite
  across a range spanning decades while the resolution stays
  proportionate to the susceptibility features being hunted.
- A step larger than the permitted fraction leaves a sub-band the unit
  is never driven at. That is a coverage defect, not a resolution
  preference: a narrow susceptibility window inside the skipped
  interval passes the test untouched.
- Covering the range means reaching both ends. A scan whose first step
  sits above the declared range start, or whose last step falls short
  of the range stop, leaves the ends unstimulated however fine the
  steps in between are.
- Dwell is governed by the unit, not by the scan. The requirement is
  the unit's own response time, held to a floor so that a unit
  declared to respond instantly is still driven long enough to be
  observed. A dwell short of that requirement makes the step a
  formality.
- The whole thing has a cost, and it is worth computing before the
  test rather than discovering it on the floor: the scan duration is
  every dwell plus the per-step settling the synthesiser and amplifier
  need, and a fraction chosen too fine can turn a range into days.

## Workflow

1. Normalize the declared scan mode. A stepped scan proceeds; a
   continuous or swept one is recorded as a finding against the clause
   rather than silently graded as though it stepped.
2. Validate the declared range: positive start, stop strictly above
   start.
3. Validate the step list: at least two steps, positive frequencies
   strictly increasing, positive dwell on every step.
4. Size each increment as a fraction of its own lower frequency and
   compare against the permitted fraction, absorbing float
   representation error at the boundary only.
5. Compute the required dwell from the unit's response time and the
   floor, then find every step held for less than that.
6. Check the first and last steps reach the ends of the declared range.
7. Total the scan duration from the dwells and the per-step settling
   time, and where a plan is being written rather than graded, generate
   a compliant stepped plan across the range.
8. Aggregate: a non-stepped mode, an unreached range end, an oversized
   increment or a short dwell each reject the scan.

## Pitfalls

- Sizing steps in fixed hertz. It is far too fine at the bottom of a
  wide range and far too coarse at the top, and the coarse end is
  where the skipped sub-bands appear.
- Reading "the generator swept from start to stop" as coverage. It
  passed through every frequency and dwelt at none, which is the case
  the clause is written against.
- Setting one dwell for the whole campaign and reusing it on a unit
  with a slow control loop or a long integration time. The stimulus is
  gone before the symptom exists.
- Counting steps instead of checking increments. A scan can have
  hundreds of steps and still contain one jump that skips a decade.
- Anchoring the plan at a convenient round frequency just inside the
  range. Both ends of the declared range have to be driven, and the
  ends are where band-edge filters and out-of-band responses live.
- Comparing an increment against the limit with a bare inequality. An
  increment meant to sit exactly on the permitted fraction can land a
  few units in the last place over and be rejected for nothing.

## Behavior contract (gate 3)

The scan-mode normalization, range and step validation, fractional
step sizing, dwell requirement and short-dwell detection, range-end
coverage, compliant step-plan generation, scan duration and the
aggregate verdict are exercised by the gate 3 contract test:
scripts/test_e2007_susceptibility_frequency_stepping.py against
scripts/e2007_susceptibility_frequency_stepping_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_susceptibility_frequency_stepping.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
