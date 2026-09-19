---
name: e31-tcs-design-general-requirements
description: "Structure the general thermal control design-to-requirements process of ECSS-E-ST-31C clause 4.4.1. Use when predicted temperatures have to become design, acceptance and qualification limits and the subsystem design drivers have to be named: turn thermal model maturity into the uncertainty margin a prediction carries, walk the hot and cold temperature stacks in the direction each case pushes, grade the design temperature against its requirement in kelvin, confirm each worst case combines consistent environment, optical-property and dissipation extremes, and rank every item by the smallest margin it keeps. Trigger: ecss, e-st-31c, thermal-design-margin-policy, thermal-model-maturity-uncertainty, thermal-worst-case-design-basis, thermal-design-driver-ranking, thermal-qualification-limit-derivation."
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
  tags: [ecss, e-st-31-thermal-scope, e31-tcs-design-general-requirements, thermal-design-margin-policy, thermal-model-maturity-uncertainty, thermal-worst-case-design-basis, thermal-design-driver-ranking, thermal-qualification-limit-derivation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — General Design Requirements (space-systems/ecss/e31-tcs-design-general-requirements)

Use when the task is the design-to-requirements step of ECSS-E-ST-31C
clause 4.4.1 — deciding what margin a predicted temperature carries, how
the design, acceptance and qualification limits follow from it, whether the
worst cases the prediction came from are worst cases at all, and which
items are actually driving the thermal design.

## Domain quick reference

- The margin a prediction carries is a property of the model, not of the
  item. An uncorrelated preliminary model earns a wide uncertainty margin;
  a model correlated against thermal balance test data earns a narrow one;
  a flight-correlated model narrower still. Quoting a predicted temperature
  without naming the maturity behind it hides the only number that makes
  it comparable with a requirement.
- The limits form a stack, and it walks outwards in the direction the case
  pushes. Predicted plus uncertainty is the design temperature; plus the
  acceptance margin is the acceptance limit; plus the qualification margin
  is the qualification limit. The cold case walks the same stack downwards,
  which is why a sign error here produces a qualification limit inside the
  design temperature.
- Compliance is graded at the design temperature, not the prediction. The
  margin is requirement minus design for the hot case and design minus
  requirement for the cold, and it is reported in kelvin so a reader can
  see how much room a redesign has to find.
- A worst case has to be internally consistent to be worth grading. A hot
  case combines the maximum environmental fluxes, end-of-life degraded
  optical properties and the maximum dissipation; a cold case the minimum
  fluxes, beginning-of-life properties and the minimum dissipation. A hot
  case run with beginning-of-life properties is optimistic by construction,
  and its margins are not margins.
- Design drivers are an output. Ranking items by the smallest margin they
  keep, with the driving case named, tells the project where the thermal
  design is actually constrained rather than where attention happens to be.

## Workflow

1. Validate each item record: a maturity level the table recognises,
   non-negative acceptance and qualification margins, and exactly a hot and
   a cold case.
2. Look up the uncertainty margin the declared model maturity earns.
3. For each case, form the design temperature from the prediction and the
   uncertainty in the direction of the case, then the acceptance and
   qualification limits from their margins.
4. Grade the design temperature against the requirement, reporting the
   margin in kelvin and absorbing representation error at exact equality
   with a named tolerance instead of relaxing the requirement.
5. Check the worst-case basis of each case: environment, optical properties
   and dissipation must all sit at the extreme the case name implies. An
   unrecognised value is refused; a recognised but wrong-direction value is
   a finding.
6. Take the smaller of the two margins as the driver of the item and name
   the case that produced it.
7. Rank the items by smallest margin, refuse two items sharing a name, and
   report the item records, the ordered design drivers and every finding.

## Pitfalls

- Applying one uncertainty margin across the whole programme. The margin
  tracks model maturity, and carrying a preliminary-model margin into a
  post-correlation review wastes design room the test campaign already
  bought.
- Deriving the qualification limit from the prediction. It is derived from
  the acceptance limit, which is derived from the design temperature; short
  circuiting the stack drops the uncertainty or the acceptance margin
  silently.
- Getting the cold-case sign wrong. The cold stack walks downwards, and a
  cold qualification limit warmer than the cold design temperature is a
  sign error, not a conservative choice.
- Grading margins from a mixed-basis case. A hot case with beginning-of-life
  optical properties or minimum dissipation understates the temperature, so
  its comfortable margin is an artefact of the case definition.
- Naming design drivers from memory. The driver is whichever item and case
  holds the smallest margin in the current run, and it moves whenever the
  model, the environment or the dissipation data is updated.

## Behavior contract (gate 3)

Maturity-to-uncertainty lookup, the hot and cold design, acceptance and
qualification stacks, kelvin margin computation with a boundary tolerance,
worst-case basis consistency findings, per-item driving case selection,
design driver ranking and the aggregate assessment are exercised by the
gate 3 contract test: scripts/test_e31_tcs_design_general_requirements.py
against scripts/e31_tcs_design_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_tcs_design_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
