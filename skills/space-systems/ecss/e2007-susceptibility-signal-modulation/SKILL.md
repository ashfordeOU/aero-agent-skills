---
name: e2007-susceptibility-signal-modulation
description: "Verify the injected-signal modulation of an EMC susceptibility run. Use when a susceptibility schedule declares a modulation, pulse rate and duty cycle per injection frequency under ECSS-E-ST-20-07C clause 5.2.10.2: confirm continuous-wave injection below the hundred-kilohertz band edge and default pulse modulation at and above it, grade the declared pulse rate and duty cycle against the default, convert an averaged reading into the peak level the unit actually sees, and separate an agreed and justified departure from an undeclared one, then reject a pulse rate that is not below the carrier it modulates. Trigger: ecss, e-st-20-07c, susceptibility-signal-modulation, pulse-modulated-injection, hundred-kilohertz-modulation-band-edge, susceptibility-injection-duty-cycle, injection-peak-to-average-ratio, emc-susceptibility-run-schedule."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-susceptibility-signal-modulation, susceptibility-signal-modulation, pulse-modulated-injection, hundred-kilohertz-modulation-band-edge, susceptibility-injection-duty-cycle, injection-peak-to-average-ratio, emc-susceptibility-run-schedule]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC Susceptibility — Injected-Signal Modulation (space-systems/ecss/e2007-susceptibility-signal-modulation)

Use when the task is the default modulation of the disturbance injected
during a susceptibility run under ECSS-E-ST-20-07C clause 5.2.10.2 --
deciding, per injection frequency, whether the carrier is presented
unmodulated or pulse-modulated, grading the declared pulse parameters
against the default, and separating a departure that was agreed from one
that was simply declared.

## Domain quick reference

- The clause sets a default, not a preference. Above a band edge at one
  hundred kilohertz the injected signal is pulse-modulated unless
  something else was agreed; below it the carrier is presented
  unmodulated. A run that injects an unmodulated carrier across the
  whole sweep has not exercised the unit the way the clause intends.
- The band edge itself belongs to the pulse-modulated side. Grading the
  exact threshold frequency as continuous-wave leaves one point of the
  sweep outside both branches.
- The default pulse parameters are quantitative: a modulation rate of
  about one kilohertz at about half duty. A rate or duty declared far
  from that is a different stimulus, and the susceptibility result it
  produces is not comparable with a default run.
- A modulation rate is only a modulation when it sits below the carrier
  it modulates. A declared rate at or above the carrier frequency is a
  recording error, not a slow modulation.
- Pulse modulation splits the level into two numbers. An averaging
  receiver reads the average; the unit responds to the peak. The peak
  stands above the average by ten times the logarithm of the reciprocal
  duty cycle -- about three decibels at half duty -- and the recorded
  injected level has to say which of the two it is.
- A departure from the default is admissible, but only as an agreed
  deviation carrying a justification. Without one it is an undeclared
  departure and the schedule cannot be graded against the clause.

## Workflow

1. Validate the run configuration: a recognized susceptibility run type,
   a positive band-edge frequency, and default pulse rate and duty cycle
   inside their physical ranges.
2. Validate each injection point: positive frequency, a recognized
   modulation, a declared level, and -- for a pulse-modulated point --
   a positive rate below the carrier and a duty cycle strictly inside
   zero and one. A continuous-wave point declaring pulse parameters is a
   contradiction and is rejected.
3. Derive the required modulation for each frequency from the band edge,
   treating the edge itself as pulse-modulated.
4. Compare the declared modulation with the required one. When they
   agree and the point is pulse-modulated, compare the declared rate and
   duty cycle with the default under a named relative and absolute
   tolerance. Absorb representation error at the tolerance edge; never
   widen the tolerance to make a point pass.
5. Categorize each point: conforming, agreed-deviation when a
   justification is carried, otherwise non-conforming.
6. Convert each declared average level to the peak the unit sees, so the
   susceptibility result can be read against either convention.
7. Aggregate: per-category counts, the first non-conforming point, the
   findings (undeclared departures) and the limitations (agreed
   deviations). The schedule is acceptable only when no point is
   non-conforming.

## Pitfalls

- Sweeping the whole band with an unmodulated carrier because the signal
  generator defaulted that way. The high-frequency half of the run is
  then not the run the clause describes.
- Grading the band-edge frequency as continuous-wave. The edge belongs
  to the pulse-modulated side.
- Declaring a duty cycle and a rate that drift from the default and
  reporting the result as a default run. The stimulus differs, so the
  threshold it produces is not comparable.
- Recording an averaged level and quoting it as the level the unit
  withstood. At half duty the peak is about three decibels higher.
- Treating an undeclared departure as an agreed one. An agreement
  without a recorded justification is not carried forward into the
  report.

## Behavior contract (gate 3)

The configuration validation, per-point validation, required-modulation
derivation, pulse-parameter tolerance grading, peak-to-average
conversion and schedule aggregation logic is exercised by the gate 3
contract test:
scripts/test_e2007_susceptibility_signal_modulation.py against
scripts/e2007_susceptibility_signal_modulation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_susceptibility_signal_modulation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
