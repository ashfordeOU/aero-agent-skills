---
name: e3102-mechanical-tests-resonance-sine-random
description: "Define and grade the resonance search, sinusoidal and random vibration runs of ECSS-E-ST-31-02C clause 5.6.10 for two-phase heat transport hardware. Use when vibration levels are set or a run is assessed against the applicable level tables, which are supplied as data: bracketing the first mode in the searched band and comparing the before and after sweeps for the frequency shift that signals damage, interpolating a sine profile on its log-log segments, sizing each sweep from its rate in octaves per minute, holding notches above the declared floor, integrating a spectral-density breakpoint table to one overall level, and applying the stage offset in decibels. Trigger: ecss, e-st-31-02c, heat-transport-vibration-campaign, low-level-resonance-search, resonance-frequency-shift-criterion, sine-sweep-octave-rate, sine-notch-depth-floor, random-psd-breakpoint-integration, vibration-level-stage-offset-db."
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
  tags: [ecss, e-st-31-02-two-phase-transport-scope, e3102-mechanical-tests-resonance-sine-random, heat-transport-vibration-campaign, low-level-resonance-search, resonance-frequency-shift-criterion, sine-sweep-octave-rate, sine-notch-depth-floor, random-psd-breakpoint-integration, vibration-level-stage-offset-db]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Mechanical Tests, Resonance Sine and Random (space-systems/ecss/e3102-mechanical-tests-resonance-sine-random)

Use when the task is the mechanical test set of ECSS-E-ST-31-02C
clause 5.6.10 -- the low-level resonance search either side of the run,
the swept-sine run, and the random run, each per axis, with their levels
and criteria taken from the applicable level tables rather than invented
here. The tables are inputs: this skill computes with them and never
hard-codes one.

## Domain quick reference

- The resonance search is not a test level, it is an instrument. A
  low-level sweep before and after the high-level runs gives two
  first-mode frequencies, and the shift between them is the damage
  indicator: a loosened joint, a cracked wick or a fluid slug shows up
  as a frequency move long before anything is visible. A searched band
  that does not bracket the first mode measures nothing at all, so the
  band is checked before the shift is.
- The shift criterion is symmetric in the sense that it is taken on
  magnitude, but the two directions mean different things. A drop is
  the usual softening signature; a rise generally means something is
  now binding that was free before. Both are findings.
- A sine profile is a straight line in log-log space between its
  breakpoints, not in linear space. Interpolating linearly between a
  low-frequency displacement-limited leg and a flat acceleration leg
  produces a level that was never specified, and asking for a level
  outside the tabulated span is an extrapolation, so it is refused.
- Sweep duration is not a free parameter. It follows from the band and
  the sweep rate: the octaves between the ends divided by the rate in
  octaves per minute. A run that quotes a duration inconsistent with
  its rate has one of the two numbers wrong.
- Notching is allowed but floored. A notch that is cut deeper than the
  declared allowance has under-tested the hardware at exactly the
  frequency the structure responds hardest, so the deepest notch across
  the checked frequencies is the number that matters, and an applied
  level above the profile is an overshoot finding in its own right.
- The overall level of a random run is an integral, not a sum of
  breakpoints. Each segment is a straight line in log-log space, so its
  area has a closed form, and the special case of a segment whose slope
  is exactly minus one has a logarithmic form instead of the general
  one. The square root of the summed areas is the overall level.
- A level stage offset moves the whole spectrum together. In density
  terms the offset is applied as a tenth-power of ten; in overall level
  terms as a twentieth-power, because the overall level is a square
  root of the density integral.

## Workflow

1. Validate every supplied table: at least two points, strictly rising
   frequency, positive levels. A table that is out of order is rejected
   rather than sorted.
2. Run the resonance search assessment: confirm the searched band
   brackets the pre-test first mode, then take the percentage shift to
   the post-test first mode and compare its magnitude against the
   declared limit.
3. Confirm the sine profile spans the whole required band, size the
   sweep from the band and the sweep rate, and multiply by the sweep
   count.
4. At each check frequency, interpolate the required and the applied
   level on their log-log segments, convert the ratio to a notch depth
   in decibels, keep the deepest, and report any applied level above the
   profile as an overshoot.
5. Integrate the random breakpoint table segment by segment to the
   overall level, apply the stage offset, and compare the delivered
   level and the run duration against what the run required.
6. Reduce each axis to one verdict, then the campaign to one verdict,
   and list any required axis that was never run.

## Pitfalls

- Reading the resonance search as a pass because nothing broke. The
  search exists to produce two numbers and their difference; a search
  reported without a before-and-after pair has not been performed for
  its purpose.
- Interpolating a sine or random table linearly in frequency. The
  breakpoints define log-log straight lines, and a linear reading of a
  steep leg can be wrong by a large factor in the middle of the
  segment.
- Summing spectral-density breakpoints to get an overall level. The
  units do not admit it, and the answer is not even close: the
  integration has to run over the segments, with the minus-one slope
  handled by its own logarithmic form rather than by a division that
  would be by zero.
- Applying a level offset to the overall level with the density factor.
  Density scales by the tenth-power of ten and the overall level by the
  twentieth-power; mixing them doubles or halves the intended change.
- Letting a notch go as deep as the shaker control loop wants. The
  floor is the whole point of allowing notching, and the deepest notch,
  not the average one, is what has to clear it.
- Comparing a shift, a notch depth, a delivered level or a duration
  against its limit by bare arithmetic. Each comes out of a logarithm
  or a division, so a case sitting exactly on its limit can land a few
  units in the last place on the wrong side; the comparisons absorb
  that representation error while the limits stay untouched.

## Behavior contract (gate 3)

The table validation, band coverage, log-log interpolation, sweep
octaves and duration, notch depth and floor, spectral-density segment
integration and overall level, decibel stage offsets, resonance shift
criterion and the per-axis and campaign verdicts are exercised by the
gate 3 contract test:
scripts/test_e3102_mechanical_tests_resonance_sine_random.py against
scripts/e3102_mechanical_tests_resonance_sine_random_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3102_mechanical_tests_resonance_sine_random.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
