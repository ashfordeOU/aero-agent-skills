---
name: q6015-total-ionising-dose-hardness-assurance
description: "Determine whether every part in an equipment survives its mission total-ionising-dose. Use when ECSS-Q-ST-60-15C clause 5.1 has to be applied to a parts list: read the local dose off the mission dose-depth curve at each part's equivalent aluminium shielding, scale it to the radiation lifetime the design must cover, divide the demonstrated dose capability by that design dose for the achieved radiation design margin, take the required margin from the evidence grade the capability rests on and the programme phase, group each part by dose sensitivity, and report the tightest part with one equipment verdict. Trigger: ecss, q-st-60-15c-clause-5-1, total-ionising-dose-hardness-assurance, radiation-design-margin, dose-depth-curve-shielding, radiation-lifetime-dose-scaling, dose-capability-evidence-grade, dose-sensitivity-grouping."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-total-ionising-dose-hardness-assurance, q-st-60-15c-clause-5-1, radiation-design-margin, dose-depth-curve-shielding, radiation-lifetime-dose-scaling, dose-capability-evidence-grade, dose-sensitivity-grouping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Total Ionising Dose (space-systems/ecss/q6015-total-ionising-dose-hardness-assurance)

Use when the task is the total-ionising-dose part of ECSS-Q-ST-60-15C
clause 5.1 — fixing the dose each part in an equipment actually has to
take, deciding how much margin its evidence obliges it to carry, and
saying from the proposal onward which component families are going to
be the problem.

## Domain quick reference

- The mission dose is not one number. The environment specification
  issues a dose-depth curve — ionising dose against equivalent
  aluminium shielding — and a part sees that curve read at the
  shielding its own box and its own location provide. Two identical
  parts at different depths in the same equipment carry different
  design doses.
- The curve is issued for a stated duration. Scaling it to the
  radiation lifetime the design has to cover is part of forming the
  design dose, not an afterthought: a five-year curve applied to a
  fifteen-year lifetime understates every margin in the equipment by
  a factor of three.
- The radiation design margin is the demonstrated dose capability
  divided by that design dose. What makes it a decision rather than a
  ratio is the required value, and that comes from the evidence the
  capability rests on. A flight-lot test earns the narrowest required
  margin; generic family data earns the widest, because the number
  being defended is a family's behaviour rather than this part's.
- Evidence grade is also a phase question. Generic family data is the
  right basis at proposal, when the part number is still a placeholder.
  Once the design is frozen the part is a specific part from a specific
  maker, and a capability still resting on family data is a finding
  regardless of how comfortable the arithmetic looks.
- A capability that rests on no radiation test at all is not a wide
  margin, it is no margin. No quotient makes it usable, so it is
  reported separately from a shortfall.
- Grouping parts by dose sensitivity is what makes the analysis useful
  early. The grouping is on the demonstrated capability, so it survives
  a change of orbit or shielding, and it is what steers selection
  toward families that will not need a waiver later.

## Workflow

1. Validate the dose-depth curve: at least two points, thickness
   strictly ascending and positive, dose positive and never rising with
   shielding. A curve that climbs with depth is an input error.
2. Validate the mission context: a positive curve duration, a positive
   required lifetime, and a programme phase from the known sequence.
3. For each part, read the local dose off the curve at its equivalent
   aluminium shielding by log-log interpolation. Refuse a shielding
   outside the tabulated span rather than extrapolating — the curve
   shape changes past its ends.
4. Scale the local dose from the curve duration to the required
   radiation lifetime to obtain the design dose.
5. Divide the demonstrated capability by the design dose for the
   achieved margin, and take the required margin from the evidence
   grade; absorb an exact equality with a named relative tolerance
   rather than by relaxing the requirement.
6. Raise the evidence findings: generic family data past design freeze,
   and a capability resting on no radiation test.
7. Group every part by the sensitivity band of its capability, pick the
   part with the lowest achieved margin as the tightest, and let the
   set of non-compliant parts decide the equipment verdict.

## Pitfalls

- Applying the headline mission dose to every part. That is the curve
  at one reference depth; it over-doses the well-shielded parts and,
  where the reference depth was generous, under-doses the exposed ones.
- Forgetting the lifetime scaling because the curve and the mission
  "both say years". The curve's duration is a property of the curve,
  and the two are equal only by coincidence.
- Using one required margin for the whole parts list. The required
  value is set by the evidence, so a list mixing lot tests with family
  data has two different bars in it.
- Treating a comfortable ratio as covering an untested capability. The
  capability is the claim under examination; a large number derived
  from it is no more supported than the claim itself.
- Letting generic family data survive design freeze because the margin
  is wide. The finding is about what the number describes, not about
  its size.
- Widening the required margin to make an exact-equality part pass. The
  equality is a representation question, settled by the tolerance
  inside the comparison.

## Behavior contract (gate 3)

The curve validation, log-log dose interpolation with its refusal
outside the tabulated span, lifetime scaling, achieved and required
margin logic, evidence-grade and programme-phase findings, sensitivity
grouping and the equipment aggregation are exercised by the gate 3
contract test:
scripts/test_q6015_total_ionising_dose_hardness_assurance.py against
scripts/q6015_total_ionising_dose_hardness_assurance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6015_total_ionising_dose_hardness_assurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
