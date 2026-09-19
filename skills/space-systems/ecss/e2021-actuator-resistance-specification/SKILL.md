---
name: e2021-actuator-resistance-specification
description: "Derive the highest actuator resistance that has to be stated across the full operating temperature and condition range, per clause 5.6.1 of ECSS-E-ST-20-21C. Use when a nominal element resistance, a temperature coefficient and a set of allowances have to become one specified maximum rather than a datasheet figure: take the hot end for a positive coefficient and the cold end for a negative one, multiply by the build tolerance and the ageing allowance, add the contact and lead contributions on top, grade the declared maximum against that worst case, and refuse a declared range narrower than the operating range. Trigger: ecss, e-st-20-21c, actuator-resistance-specification, maximum-actuator-resistance, resistance-temperature-coefficient, operating-range-coverage, bridgewire-resistance-adders, ageing-resistance-allowance."
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
  tags: [ecss, e-st-20-21-actuator-interface-scope, e-st-20-21c-clause-5-6-1, e2021-actuator-resistance-specification, e-st-20-21c, actuator-resistance-specification, maximum-actuator-resistance, resistance-temperature-coefficient, operating-range-coverage, bridgewire-resistance-adders]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuator Interface — Actuator Resistance Specification (space-systems/ecss/e2021-actuator-resistance-specification)

Use when the task is clause 5.6.1 of ECSS-E-ST-20-21C: the actuator
specification has to state the highest resistance the actuator can
present, and state it across the whole operating temperature and
condition range. This leaf builds that number from the element and its
allowances, and grades a declared maximum against it.

## Domain quick reference

- The quantity the interface needs is the maximum, not the nominal. The
  firing current is set by the loop, so the resistance that decides
  whether the current still reaches its floor is the highest one the
  actuator can present, over every temperature and condition it will
  see.
- Which end of the temperature range is the worst case depends on the
  sign of the coefficient. A positive coefficient puts the maximum at
  the hot end; a negative one puts it at the cold end. Measuring at hot
  soak alone is correct for one of those and blind for the other.
- The temperature model is linear around a reference point, and it has a
  validity limit. A coefficient large enough to drive the computed
  resistance to zero or below over the declared range is not a small
  extrapolation error; it says the linear form does not hold there and
  the point is refused rather than reported.
- The allowances divide into two kinds. The build tolerance and the
  ageing allowance are proportional and multiply the element; the
  contact and lead contributions are absolute and add. On a low
  resistance bridgewire the absolute pair can dominate the stack, which
  is why they are never folded into a percentage.
- A declaration that repeats the reference resistance is its own finding.
  It is not a maximum that came out slightly low; it is a datasheet
  figure with no stack applied, and reporting it as a small shortfall
  invites it to be closed by a small edit.
- The declaration carries a range as well as a number. A range narrower
  than the operating range leaves part of the mission unspecified, and
  since the firing current is computed from this maximum, that gap
  propagates into an interface nobody verified.

## Workflow

1. Validate the operating range and the element: a maximum temperature
   not below the minimum, a positive reference resistance, and a finite
   coefficient and reference temperature.
2. Choose the worst-case end from the sign of the coefficient and take
   the temperature at that end of the operating range.
3. Evaluate the element resistance there, refusing a result at or below
   zero rather than reporting a value the linear model cannot support.
4. Multiply by the build tolerance and the ageing allowance, then add
   the contact and lead contributions, keeping the proportional and the
   absolute parts distinct in the record.
5. Grade the declared maximum against that worst case, absorbing
   floating-point representation error at an exact match with a named
   tolerance rather than by lowering the computed value.
6. Raise a separate finding when the declared maximum simply repeats the
   reference resistance while a non-zero coefficient is in play, because
   the defect is a missing stack rather than a small shortfall.
7. Compare the declared temperature range against the operating range
   and report each end it fails to reach, then grade a set on the
   declaration holding the least margin.

## Pitfalls

- Specifying the nominal resistance. The interface needs the maximum;
  the nominal understates the loop, overstates the firing current and
  makes a compatibility case pass that the cold or hot unit fails.
- Assuming the hot end is always the worst case. A negative coefficient
  moves it to the cold end, and a hot-soak measurement then certifies
  the end of the range where the resistance is lowest.
- Folding the contact and lead resistance into a percentage allowance.
  They are absolute, so on a low-resistance element the percentage
  understates them by a wide margin and on a high-resistance element it
  overstates them.
- Leaving the ageing allowance out because the actuator has not aged
  yet. The specification is a statement for the whole mission, and the
  firing may be the last event of it.
- Extrapolating the linear coefficient across a range that drives the
  resistance non-positive. The arithmetic still produces a number; it is
  simply not a resistance.
- Stating the maximum over the qualification range while the mission
  operates wider. The unstated part of the range is where the
  compatibility case has no evidence at all.

## Behavior contract (gate 3)

The range validation, worst-case end selection, linear temperature
model with its validity refusal, proportional and absolute allowance
stack, declared-maximum grading, nominal-only detection and range
coverage are exercised by the gate 3 contract test:
scripts/test_e2021_actuator_resistance_specification.py against
scripts/e2021_actuator_resistance_specification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_actuator_resistance_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
