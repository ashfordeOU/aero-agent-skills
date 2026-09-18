---
name: e2007-power-lead-transient-procedure
description: "Verify a power-lead transient application run against ECSS-E-ST-20-07C clause 5.4.9.4: sequence the mandatory steps, confirm the instrument stabilisation check brackets the pulses rather than trailing them, grade the differential-mode and common-mode applications for both polarities, pulse count, pulse width and the recovery interval between pulses, compute the elapsed application time and the read-back drift the bracketing checks leave, and separate a genuine susceptibility from an instrument that simply moved, carrying a polarity driven short of its required count as a limitation rather than as a finding. Use when running or auditing a power-lead transient susceptibility run. Trigger: ecss, e-st-20-07c, power-lead-transient-procedure, differential-mode-pulse-application, common-mode-pulse-application, transient-instrument-stabilisation-check, transient-pulse-recovery-interval, transient-polarity-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-power-lead-transient-procedure, differential-mode-pulse-application, common-mode-pulse-application, transient-instrument-stabilisation-check, transient-pulse-recovery-interval, transient-polarity-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Power-Lead Transient Procedure (space-systems/ecss/e2007-power-lead-transient-procedure)

Use when the task is the application procedure of ECSS-E-ST-20-07C clause
5.4.9.4 -- the order the pulses are driven in, the differential and common
mode applications the clause requires of each other, and the instrument
stabilisation checks that decide whether the run's observation can be
attributed to the unit at all.

## Domain quick reference

- Both modes are required and they are not interchangeable. The
  differential application drives the pulse between a supply lead and its
  own return; the common application drives every lead together against
  the structure. A unit can ride out one and fall over on the other,
  because the two excite different parts of the input filter, so a run
  that applied only the differential pulses has not covered the clause.
- Both polarities are required of each mode. Input protection is rarely
  symmetric -- a clamp diode that swallows one polarity conducts the other
  into the regulator -- so a single-polarity run reports the easy half.
- Pulse count is part of the stimulus, not a convenience. A transient
  susceptibility that only appears once the unit has been hit repeatedly
  is a real susceptibility, and a run of two pulses cannot see it.
- The recovery interval between pulses exists so the unit and the bench
  both settle. Pulsing faster than the interval stacks the responses, and
  the level at which the unit finally trips belongs to the stacking rather
  than to the specified pulse.
- Pulse width is a window. A narrow pulse carries less energy into the
  unit for the same amplitude, so a run at half the width is not a more
  conservative run, it is a different test.
- The stabilisation check has to bracket the application: once before the
  first pulse and once after the last. Taken only afterwards it cannot
  tell whether the instrument read differently all along.
- Instrument drift outranks the observation. When the bracketing checks
  disagree by more than the allowed decibels, neither an upset nor a clean
  run can be attributed, and the result is inconclusive rather than a pass
  or a fail.
- Too few pulses at a polarity that was nevertheless driven is a
  limitation to carry; a polarity never driven at all is a finding. The
  two look alike in a log and mean different things in a report.

## Workflow

1. Sequence the run's steps: name the missing ones and detect an order
   that puts a pulse application before its bracketing check.
2. Compute the warm-up headroom against the required soak, keeping the
   sign so a short soak is visible as a shortfall.
3. Compute the read-back drift between the bracketing stabilisation checks
   and decide whether the instrument stayed trustworthy.
4. Grade each mode application: normalize the polarities, reject a
   polarity recorded twice, name the polarities never driven, and separate
   them from the polarities driven short of the required count.
5. Grade the pulse width against its window and the recovery interval
   against its floor, then compute the elapsed application time.
6. Group the run's observation once the instrument's own behaviour is
   known: susceptible, tolerant, or inconclusive because the instrument
   moved.
7. Aggregate: findings reject the procedure, limitations are carried, and
   a run is valid only when no finding stands.

## Pitfalls

- Applying the differential pulses, finding nothing, and stopping. The
  common-mode path through the chassis is the one that usually bites.
- Driving a single polarity because the generator was already set that
  way, and reporting a symmetric result.
- Firing the pulses back to back to save bench time, so the unit is graded
  against stacked responses rather than the specified transient.
- Narrowing the pulse to protect the unit and treating the result as
  conservative. The energy delivered fell with the width.
- Taking the stabilisation check only at the end of the run, which cannot
  distinguish an instrument that drifted from one that always read that
  way.
- Reporting an upset as a susceptibility when the bracketing checks
  disagree. The observation belongs to the instrument until proven
  otherwise.
- Logging a polarity driven three times and a polarity never driven as the
  same shortfall.

## Behavior contract (gate 3)

The step sequencing, warm-up headroom, stabilisation-drift and instrument
stability decision, per-mode polarity, count, width and interval grading,
elapsed-time computation, outcome grouping and run aggregation logic is
exercised by the gate 3 contract test:
scripts/test_e2007_power_lead_transient_procedure.py against
scripts/e2007_power_lead_transient_procedure_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_power_lead_transient_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
