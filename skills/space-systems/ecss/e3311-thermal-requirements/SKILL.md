---
name: e3311-thermal-requirements
description: "Evaluate the thermal environment and thermal stability of an explosive device against ECSS-E-ST-33-11C clause 4.8.3. Use when the task is showing that a charge survives its mission thermally: widening the predicted hot and cold extremes by the declared uncertainty and grading both against the qualification limits, holding the hottest prediction clear of the decomposition-onset temperature by the required margin, and converting the mission thermal profile into equivalent time at the qualification dwell temperature through an Arrhenius acceleration factor so cumulative time at temperature is compared with the dwell the device was qualified over. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-thermal-stability, arrhenius-decomposition-life, explosive-temperature-envelope, decomposition-onset-margin, cumulative-thermal-damage-explosive, pyrotechnic-qualification-dwell."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-thermal-requirements, explosive-thermal-stability, arrhenius-decomposition-life, explosive-temperature-envelope, decomposition-onset-margin, cumulative-thermal-damage-explosive, pyrotechnic-qualification-dwell]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Thermal Requirements (space-systems/ecss/e3311-thermal-requirements)

Use when the task is the thermal screen of ECSS-E-ST-33-11C clause
4.8.3 -- showing that the temperatures an explosive device actually
sees, and the time it spends at them, leave the charge as energetic and
as stable at the end of the mission as the qualification proved it at
the start.

## Domain quick reference

- Temperature does two separate things to an explosive, and the clause
  asks about both. One is instantaneous: is the device outside the
  range it was qualified over, or near the temperature at which the
  composition begins to decompose. The other is cumulative: how much
  of its chemical life the mission has spent.
- The envelope check is run on the predicted extremes widened by the
  declared prediction uncertainty, never on the bare prediction. The
  uncertainty pushes the hot case up and the cold case down at the
  same time, so one declared number moves both bounds inward.
- The decomposition-onset check is separate from the qualification
  envelope and usually looser, but it is the one that matters when a
  device is qualified to a range someone picked from a catalogue
  rather than from the composition's own chemistry.
- Cumulative damage is not linear in time or in temperature. The
  decomposition rate follows an Arrhenius law, so an acceleration
  factor converts each profile segment into equivalent time at the
  qualification dwell temperature, and the segments then simply add.
- The consequence of that exponential is the result that surprises
  reviewers: a short excursion a few tens of kelvin above the dwell
  temperature can outweigh years of cruise, and a device that never
  once exceeded its hot limit can still have consumed its entire
  qualified dwell.
- The activation energy is a property of the composition, measured for
  it, not a constant of the method. A default is supplied so the
  arithmetic runs, and a project substitutes its own measured value.
- Utilization is reported as a fraction of the qualified dwell rather
  than as a pass mark alone, because the number a reviewer needs is
  how much life is left, not merely whether any remains.

## Workflow

1. Fix the qualification range and reject a case whose declared cold
   limit is not below its hot limit, because every margin below
   inherits the sign convention from that ordering.
2. Widen both predicted extremes by the prediction uncertainty, then
   grade the hot and cold margins separately against the required
   qualification margin and name whichever bound failed.
3. Grade the hottest widened prediction against the decomposition
   onset temperature with its own margin, and keep that verdict
   distinct from the envelope verdict.
4. Normalize the mission thermal profile: every segment needs a
   temperature and a duration, a profile with no time in it is a
   rejected input, and the hottest segment is recorded because it is
   almost always the one that drives the answer.
5. Convert each segment to equivalent time at the qualification dwell
   temperature through the Arrhenius factor, sum them, and express the
   total as a utilization of the qualified dwell.
6. Close with the three verdicts, the driving segment and the
   utilization, so a failing case names both what broke and what would
   have to change.

## Pitfalls

- Grading the bare predicted temperatures and holding the uncertainty
  in a separate column. The uncertainty is part of the prediction for
  this purpose, and a case that passes on the nominal and fails on the
  widened value is a case that fails.
- Reading a hot limit as a decomposition limit. The qualification
  range says what was demonstrated; the onset temperature says what
  the chemistry does. A device can be well inside the first and
  uncomfortably close to the second.
- Averaging the mission temperature before applying the rate law. The
  rate is exponential in temperature, so the average of the rates is
  not the rate at the average, and averaging first always understates
  the damage.
- Treating time below the dwell temperature as free. It is
  discounted, not zero, and on a mission long enough the discounted
  cruise can still be the larger term.
- Carrying a textbook activation energy for a composition nobody
  measured. It sets the exponent, so an error there scales the whole
  equivalent time, and the result inherits a precision it never had.
- Comparing utilization with its limit by bare arithmetic. It is a
  quotient of sums of exponentials, so a mission sitting exactly on
  its dwell can land a few units in the last place above it; the
  comparison absorbs that while the dwell stays untouched.

## Behavior contract (gate 3)

The unit conversion, profile normalization, Arrhenius acceleration
factor, equivalent-time summation, envelope and onset margins,
utilization grading and overall verdict are exercised by the gate 3
contract test: scripts/test_e3311_thermal_requirements.py against
scripts/e3311_thermal_requirements_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3311_thermal_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
