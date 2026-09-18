---
name: e2020-power-distribution-standard-assumptions
description: "Evaluate a protection-device application against the baseline assumptions of ECSS-E-ST-20-20C clause 4.2. Use when a latching current limiter is reused outside the host unit qualification temperature range and the power bus behaviour its requirements were written on: refuse an unstated, inverted or self-contradictory baseline, take the cold, hot, low-voltage and high-voltage margins one by one, admit an application landing exactly on a bound, name the limiting margin, and raise an advisory for an application sitting inside the marginal band. Trigger: ecss, e-st-20-20c-clause-4-2, host-unit-qualification-temperature-baseline, power-bus-voltage-baseline-assumption, protection-device-application-envelope, baseline-envelope-limiting-margin, requirement-applicability-deviation."
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
  tags: [ecss, e-st-20-20-power-protection-device-scope, e2020-power-distribution-standard-assumptions, host-unit-qualification-temperature-baseline, power-bus-voltage-baseline-assumption, protection-device-application-envelope, baseline-envelope-limiting-margin, requirement-applicability-deviation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Protection Devices -- Standard Assumptions (space-systems/ecss/e2020-power-distribution-standard-assumptions)

Use when the task is the clause 4.2 applicability question of
ECSS-E-ST-20-20C: the requirements on a protection device were written
on a stated baseline -- the temperature range the host unit is qualified
over and the way the power bus it is fed from behaves -- and a
particular application has to be shown to sit inside it before those
requirements can be claimed to apply.

## Domain quick reference

- The baseline is what makes the downstream numbers portable. Trip
  thresholds, voltage-drop limits and off-state leakage figures were all
  written for a device living inside one envelope, so moving the device
  out of that envelope moves it out of the argument that justifies them.
- Qualification temperature is a property of the host unit, not of the
  limiter alone. A limiter reused unchanged in a hotter mounting is a
  new application of the same part, and the baseline it inherits is the
  new host's, not the one it came from.
- Bus behaviour is the second half and is stated as a range, not a
  point. A device that sees the nominal voltage all its life is not the
  case the requirements were sized for; the case is the bus at its
  lowest and at its highest, which is where trip behaviour and drop
  actually bite.
- Four margins carry the whole judgement: how much colder the baseline
  is qualified than the application gets, how much hotter, how far the
  bus may sag below the application's lowest voltage, and how far it may
  rise above the application's highest. All four are signed the same
  way, positive meaning inside the baseline.
- The two kinds are not commensurable. A five-kelvin margin and a
  half-volt margin cannot be ranked against each other, so the tighter
  thermal assumption and the tighter electrical assumption are reported
  separately with their units named.
- A bound is inclusive. An application reaching exactly the
  qualification temperature is inside the envelope, and the comparison
  tolerance exists to absorb representation error rather than to widen
  the baseline.
- Stepping outside is not automatically a failure of the device. It is
  a failure of the applicability argument, and the correct output is a
  deviation to be dispositioned, not a quiet re-use.

## Workflow

1. Validate the marginal-band policy first: the temperature band and
   voltage band inside which a met assumption is still called out. A
   non-positive band is refused rather than treated as "no advisories".
2. Read the baseline. An absent assumption set, or one whose reference
   is blank, closes the assessment on baseline assumption not stated,
   because there is nothing an applicability claim can point at.
3. Check the baseline for sense: a qualification range that actually
   spans, a bus range that actually spans, positive bus voltages, and a
   nominal voltage sitting inside its own stated range. A collapsed or
   inverted range is a transcription defect, not a hard application.
4. Validate the application: a named unit, a maximum temperature not
   below its minimum, and a maximum bus voltage not below its minimum.
5. Form the four signed margins, positive meaning inside the baseline,
   and keep them in their own units.
6. Name every assumption the application steps outside of -- all of
   them, not the first found -- and report the limiting thermal and
   limiting electrical assumption with its margin and unit.
7. Raise a marginal advisory for each met assumption sitting inside the
   policy band. Advisories are reported with the verdict and do not
   move it.
8. Close on one verdict: baseline assumption not stated, application
   outside baseline envelope, or application within baseline envelope.

## Pitfalls

- Carrying the previous programme's qualification range across with the
  part. The range belongs to the host unit, and a new mounting is a new
  baseline whether or not the limiter changed.
- Judging the application at the nominal bus voltage. The requirements
  were sized at the extremes of the bus range, and a nominal-only check
  never exercises the conditions that produced the numbers.
- Ranking a kelvin against a volt. The smallest number among the four
  margins is not the limiting one unless the units match, and reporting
  it as such picks the wrong assumption to defend.
- Treating a bound as exclusive. An application reaching exactly the
  qualification temperature is inside the envelope; pushing it out on a
  representation difference invents a deviation.
- Absorbing a breach as engineering judgement. Stepping outside the
  baseline does not mean the device fails -- it means the standard's
  argument no longer covers it -- and the output is a deviation someone
  dispositions, not silence.
- Reporting a verdict with no margin beside it. An application holding
  on half a volt and one holding on five volts carry the same word and
  very different exposure to the next model update.

## Behavior contract (gate 3)

The marginal-band policy validation, baseline validation including the
collapsed and inverted ranges and the nominal-inside-range check, the
application validation, the four signed margins, the breach list, the
limiting thermal and electrical assumptions, the marginal advisories and
the applicability verdict are exercised by the gate 3 contract test:
scripts/test_e2020_power_distribution_standard_assumptions.py against
scripts/e2020_power_distribution_standard_assumptions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_power_distribution_standard_assumptions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
