---
name: e2008-sca-electrical-parameter-test-purpose
description: "Determine whether the electrical parameter test on a solar cell assembly establishes the parameter set solar generator design actually consumes, under ECSS-E-ST-20-08C clause 6.4.3.3.1: map each parameter to the design activity that reads it, derive what the measured set already implies instead of demanding it twice, cross-check maximum power against the current and voltage reported at that point, fit each temperature coefficient across its measured span, compare every uncertainty with what the design margin needs, and name the design activities a missing, contradictory or coarse parameter blocks. Use when scoping or reviewing the assembly electrical parameter test that feeds generator design. Trigger: ecss, e-st-20-08c, clause-6-4-3-3-1, solar-cell-assembly-electrical-parameters, solar-generator-design-input-parameters, assembly-fill-factor-consistency, assembly-temperature-coefficient-span, electrical-parameter-uncertainty-adequacy."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-sca-electrical-parameter-test-purpose, solar-cell-assembly-electrical-parameters, solar-generator-design-input-parameters, assembly-fill-factor-consistency, assembly-temperature-coefficient-span, electrical-parameter-uncertainty-adequacy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- SCA Electrical Parameter Test Purpose (space-systems/ecss/e2008-sca-electrical-parameter-test-purpose)

Use when the task is to state and defend why the electrical parameters
of a solar cell assembly are established under ECSS-E-ST-20-08C clause
6.4.3.3.1 -- what the test hands the solar generator designer, and
whether what it hands over is usable.

## Domain quick reference

- The test has a customer. Every parameter it establishes is read by a
  named generator design activity -- string current sizing, string
  length sizing, the power budget, bus voltage matching, cell selection,
  the cold-case voltage margin, the hot-case current margin -- and a
  parameter that no activity reads is not a purpose, it is a habit.
- A derived parameter is not a second measurement. Maximum power follows
  from the current and voltage at that point; fill factor follows from
  maximum power against the short-circuit and open-circuit readings.
  Demanding them separately overstates what the test has to do, and the
  derivation carries its own combined uncertainty.
- A temperature coefficient is a fitted slope, not a reading. It needs
  measured points either side of the reference, and it carries the span
  it was fitted across as part of its meaning.
- A coefficient's uncertainty is set by the span, not by the instrument.
  The same reading uncertainty divided by a smaller measured change is a
  larger relative uncertainty on the slope, which is why a coefficient
  taken over a narrow span supports no margin at all even when every
  reading behind it was excellent.
- Established is not the same as consistent. A reported maximum power
  that disagrees with the current and voltage reported at that point, or
  a set implying a fill factor no assembly can deliver, is a set whose
  numbers are wrong rather than merely absent.
- Parameters established at the wrong condition describe a different
  article. A reading taken away from the reference irradiance and
  temperature the design reads is not converted into one by being
  tabulated next to it.
- Adequate is a third question. A parameter can be present, consistent
  and still too coarsely known for the margin that consumes it, and the
  activity that reads it is blocked exactly as if it were missing.

## Workflow

1. Validate the policy first: the required parameter list, a usable
   uncertainty limit for each, the power consistency tolerance, the
   minimum temperature span and the reference condition.
2. Read the declared measurements, refusing a parameter no design
   activity reads and a reading with no stated uncertainty.
3. Fill the set out by derivation -- maximum power from its current and
   voltage, fill factor from the established set -- without displacing
   anything that was actually measured.
4. Fit each temperature coefficient across its series, and leave it
   unestablished when the span is shorter than a usable slope needs.
5. Check consistency: the reported condition against the reference, the
   reported maximum power against its own operating point, and the
   implied fill factor against what is physically possible.
6. Compare every established parameter with the uncertainty its design
   activity needs, then close on one verdict -- inconsistent, incomplete,
   uncertainty-insufficient or established -- with the design activities
   supported and blocked named alongside it.

## Pitfalls

- Listing parameters without naming who reads them. The list then cannot
  say what a gap costs, and a missing coefficient looks like a missing
  row rather than an unsupported cold-case margin.
- Requiring maximum power and fill factor to be measured separately. The
  set already implies them, and the extra measurement adds cost without
  adding information.
- Quoting a temperature coefficient without its span. Two coefficients
  with the same value and the same instrument can differ by an order of
  magnitude in usefulness, and only the span says which is which.
- Accepting a parameter set whose own numbers disagree. A maximum power
  that does not match its operating point means one of the three is
  wrong, and averaging the disagreement away hides which.
- Treating a coarse parameter as a soft pass. The design activity that
  reads it is blocked just as firmly as by an absent one.
- Comparing an uncertainty with its limit by bare arithmetic. A value
  landing exactly on the limit can evaluate a few units in the last
  place above it, so the comparison absorbs that representation error
  while the limit itself stays untouched.

## Behavior contract (gate 3)

The policy validation, the fill factor and power consistency
computations, the fitted temperature coefficients and their span-driven
uncertainty, the derivation of an implied parameter, the design activity
mapping and the four-way purpose verdict are exercised by the gate 3
contract test:
scripts/test_e2008_sca_electrical_parameter_test_purpose.py against
scripts/e2008_sca_electrical_parameter_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_electrical_parameter_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
