---
name: e2020-startup-current-slew-limit
description: "Evaluate whether a unit holds its output-current rise inside the declared turn-on slew ceiling, per ECSS-E-ST-20C clause 5.4.2.1.1. Use when turn-on traces from several worst-case corners have to be judged rather than one nominal switch-on: validate the time base, slope every segment, take the steepest rising stretch rather than the final current over the total rise time, compare it with the ceiling at inclusive equality, carry the relative headroom, and flag a trace sampled too coarsely to show the slope it reports or a corner the campaign never reached. Trigger: ecss, e-st-20-electrical-scope, startup-current-slew-limit, turn-on-current-rise-rate, peak-rising-slew-segment, slew-ceiling-headroom-fraction, coarse-sampling-peak-smoothing, turn-on-corner-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-startup-current-slew-limit, turn-on-current-rise-rate, peak-rising-slew-segment, slew-ceiling-headroom-fraction, coarse-sampling-peak-smoothing, turn-on-corner-coverage, output-current-slew-ceiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Startup Current Slew Limit (space-systems/ecss/e2020-startup-current-slew-limit)

Use when the task is the turn-on rise-rate requirement of ECSS-E-ST-20C
clause 5.4.2.1.1 -- showing that while the device is switching on, the
output current climbs no faster than the declared ceiling, rather than
merely arriving at the right current in the end.

## Domain quick reference

- The requirement is on a slope, not on a current. Everything
  downstream of the switch was sized against that slope: the harness
  inductance turns a rate of rise into a voltage, the source has to
  follow the step without sagging, and the neighbouring lines pick the
  transient up as conducted and radiated noise.
- The peak segment governs, not the mean. Final current divided by
  total rise time hides every fast stretch inside a slow-looking ramp,
  and that averaged number is the one a unit passes with while its real
  slope is several times the ceiling.
- A trace cannot show a slope faster than its own time base. Samples
  taken further apart than the fast stretch lasts smooth the peak away,
  so the sampling interval is part of the evidence rather than an
  implementation detail, and a comfortable slope on a coarse trace is
  an artefact rather than a result.
- The ceiling is held at the corner, not at the bench nominal. Turn-on
  slope moves with temperature, bus voltage and the capacitance the
  load presents, so a campaign that misses a declared corner has not
  demonstrated the ceiling there however comfortable its other traces
  look.
- A trace that never rises is not evidence of a turn-on. It carries no
  slope to judge, and reading it as a comfortable pass is the quietest
  way to close this clause on nothing.
- The comparison is inclusive. A peak landing exactly on the ceiling
  meets the requirement, and the tolerance exists to absorb
  representation error rather than to lift the ceiling.

## Workflow

1. Read the declared rise-rate ceiling. Without it there is nothing a
   measured slope can be judged against and the assessment closes.
2. Validate each turn-on trace as a time series: two samples at least,
   times rising, currents real and never negative.
3. Slope every segment of the trace and take the steepest rising one.
   Carry the mean ramp alongside it so the gap between the two is
   visible rather than assumed.
4. Compare the peak with the ceiling at inclusive equality and record
   the headroom as a fraction of the ceiling, negative when passed.
5. Check the coarsest gap in each time base against the interval the
   fast stretch needs, and name any trace whose peak may have been
   smoothed rather than measured.
6. Compare the corners the campaign reached against the corners it was
   required to reach, and report the worst trace by headroom, every
   finding, and the advisories.

## Pitfalls

- Quoting the averaged rise rate. It is the number that passes, and it
  is not the number the clause asks for; the two diverge most exactly
  where the design is weakest.
- Accepting a trace whose sampling interval is longer than the fast
  stretch. The peak is then a property of the oscilloscope setting
  rather than of the unit, and re-measuring at a finer time base is the
  only way to tell.
- Treating turn-on slope as a bench constant. Cold silicon into a large
  load capacitance at the top of the bus range is a different waveform
  from the one the nominal bench run produces.
- Closing the clause on a flat trace. A capture that starts and ends at
  the same current shows no turn-on, and a pass read off it is a pass
  read off nothing.
- Comparing a peak with the ceiling by bare arithmetic. The peak comes
  out of a division, so a slope sitting exactly on the ceiling can fall
  a few units in the last place outside; the comparison absorbs that
  representation error while the declared ceiling stays untouched.

## Behavior contract (gate 3)

The trace validation, segment slopes, peak-versus-mean rise rate,
sampling-interval advisory, headroom fraction, corner coverage and
worst-trace report are exercised by the gate 3 contract test:
scripts/test_e2020_startup_current_slew_limit.py against
scripts/e2020_startup_current_slew_limit_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_startup_current_slew_limit.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
