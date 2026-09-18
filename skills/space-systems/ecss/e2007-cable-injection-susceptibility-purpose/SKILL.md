---
name: e2007-cable-injection-susceptibility-purpose
description: "Verify that the aim of ECSS-E-ST-20-07C clause 5.4.8.1 is actually demonstrated: confirm every required harness bundle was swept across the band with no step wider than the grid allows, take the current the bench drove against the level required at each frequency, form the drive margin in decibels, categorize each point as meeting, sitting on or short of that level, grade where a performance deviation first appeared against it, reduce every bundle to its worst frequency and name the governing bundle, and refuse a sweep whose frequencies do not advance. Use when grading a sine-wave cable injection susceptibility run. Trigger: ecss, e-st-20-07c, cable-injection-susceptibility-purpose, bulk-current-injection-sweep, injection-drive-margin-db, injection-frequency-grid-coverage, injection-susceptibility-threshold, governing-injection-bundle."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-cable-injection-susceptibility-purpose, bulk-current-injection-sweep, injection-drive-margin-db, injection-frequency-grid-coverage, injection-susceptibility-threshold, governing-injection-bundle]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Cable Injection Susceptibility Purpose (space-systems/ecss/e2007-cable-injection-susceptibility-purpose)

Use when the task is the aim of ECSS-E-ST-20-07C clause 5.4.8.1 -- deciding
whether a completed injection run actually shows that a unit keeps working
while sine wave currents are coupled onto the cables and leads that reach
it, at the levels the interface specifies, across the whole band those
levels are specified over.

## Domain quick reference

- The clause is about currents on the harness, not fields in a chamber.
  Radiated coupling onto a spacecraft harness concentrates into common-mode
  current, and injecting that current directly reproduces the interference
  the unit will really see for a fraction of the power a field test needs.
- Two different things are being demonstrated at once and a run can fail at
  either. The unit has to ride out the specified level; the bench has to
  have actually applied that level. A point where the amplifier ran out of
  drive is not a pass, it is an untested frequency wearing a pass.
- The drive margin is the decibel difference between the current the monitor
  probe recorded and the current the level asks for. It is the number that
  travels, because it says how much of the run was margin and how much was
  the bench sitting on its limit.
- Where a deviation first appears is more useful than whether one appeared.
  A threshold well above the specified level is a characterised unit with
  known headroom; a threshold on the level is a finding, because the next
  build, the next harness and the next bench all move it downward.
- Coverage is part of the aim. Levels are specified over a band, and a sweep
  that skips a stretch of that band has not demonstrated anything there. A
  resonance on a harness bundle is narrow, and the grid density is what
  decides whether the sweep can walk past one.
- Every bundle is judged separately. A power harness, a signal harness and a
  pyro line do not carry the same current for the same drive and do not
  couple into the same part of the unit. The governing result is the worst
  bundle at its worst frequency, never an average across bundles.
- A sweep whose frequencies do not advance is not a sweep. It cannot be
  checked for gaps, and sorting it silently invents coverage that was never
  recorded.

## Workflow

1. Validate every record: a named bundle, positive frequency, positive
   required and achieved currents, and a deviation onset that is either
   absent or positive.
2. Group the records by bundle and validate each group as a sweep -- at
   least two points, frequencies strictly advancing, one bundle per sweep.
3. Compare each sweep's frequency list against the grid the band asks for,
   reporting the stretches left uncovered at either end and in between.
4. Form the drive margin at each point and categorize it as meeting the
   level, sitting on it, or short of it, absorbing representation error at
   the level with a named tolerance rather than by relaxing the level.
5. Where a deviation was recorded, form the threshold margin against the
   required level and categorize the response above or at-and-below it.
6. Reduce each point to its governing margin, each bundle to its worst
   point, and the required bundles to the governing bundle and frequency.
7. Aggregate: gaps, drive shortfalls, deviations at or under the level and
   uninjected required bundles are findings; points on the level, thresholds
   just above it and unrequired bundles are limitations. The aim stands only
   when no finding stands.

## Pitfalls

- Reading a sweep as a pass because nothing misbehaved, without checking
  that the specified current was reached at every point.
- Recording that the unit was susceptible without recording the current at
  which it became so, which throws away the only number that says whether
  there was any headroom.
- Setting the grid by habit rather than by the band. A coarse grid walks
  straight past a harness resonance, and the run then reports margin the
  unit does not have.
- Sweeping the power harness and assuming the signal bundles follow. They
  have different common-mode impedance and reach different circuits.
- Averaging margins across bundles or across frequency. The demonstration
  lives at the worst point, and an average hides it.
- Treating a point that lands exactly on the required level as a clean pass
  and recording nothing, so the next build has no warning there was never
  any margin.
- Sorting a record whose frequencies do not advance to make it checkable,
  which fabricates coverage rather than rejecting a bad capture.

## Behavior contract (gate 3)

The record and sweep validation, grid coverage-gap detection, drive-margin
formation and three-valued categorization, deviation-threshold grading,
per-bundle worst-case reduction, governing-bundle selection and the
aggregate verdict are exercised by the gate 3 contract test:
scripts/test_e2007_cable_injection_susceptibility_purpose.py against
scripts/e2007_cable_injection_susceptibility_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_cable_injection_susceptibility_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
