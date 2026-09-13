---
name: e2001-analysis-margin-strategy
description: "Use when derive the multipaction margin-strategy of ECSS-E-ST-20-01C clause 5.3.3.1 from the data actually in hand: categorize the dimension-basis as measured-hardware, tolerance-worst-case or nominal-design and the secondary-emission basis as surface-measured, material-measured or generic-literature, take the smallest credible gap and a bounding-yield-curve wherever a basis is weak, build up the required multipaction-margin in decibel from those two shortfalls and the failure-consequence, then compare the achieved multipaction-margin and name the measurement that would retire the largest increment. Trigger: ecss, e-st-20-electrical-scope, multipaction-margin-strategy, dimensional-data-basis, yield-data-basis, tolerance-worst-case-gap, bounding-yield-curve, margin-build-up, as-built-gap-measurement."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-analysis-margin-strategy, multipaction-margin-strategy, dimensional-data-basis, yield-data-basis, tolerance-worst-case-gap, bounding-yield-curve, margin-build-up, as-built-gap-measurement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Analysis Margin Strategy (space-systems/ecss/e2001-analysis-margin-strategy)

Use when the task is the margin-strategy choice of ECSS-E-ST-20-01C
clause 5.3.3.1 -- deciding, before the numbers are run, which
multipaction-margin the analysis has to carry given how well the two
governing inputs are actually known: the critical gap dimension and the
secondary-emission yield of the electrode surface.

## Domain quick reference

- A multipaction prediction rests on two inputs that are never known
  exactly. The gap sets the resonance condition, and the
  secondary-emission yield of the electrode surface sets whether the
  electron population grows. The margin is the price paid for how
  loosely each one is pinned down, so the strategy is chosen from the
  data basis, not from preference.
- Dimension basis, best to weakest: measured-hardware (the flight gap
  was measured after build), tolerance-worst-case (the smallest gap the
  drawing tolerance permits, which is the multipaction-driving
  extreme), and nominal-design (the drawing value with no stack at
  all). Tightening a gap lowers the breakdown level, so the worst case
  is the small end of the tolerance band, never the mean.
- Yield basis, best to weakest: surface-measured (a curve measured on
  the production finish, which carries the real roughness, coating and
  conditioning state), material-measured (a curve measured on the base
  material, missing the finish), and generic-literature (a tabulated
  family curve that is not a property of this surface at all).
- A generic yield basis is admissible only against a bounding value.
  The tabulated curve describes a material family, so the analysis
  carries whichever peak yield is higher, the declared value or the
  bounding family value, and records that substitution.
- The required multipaction-margin is built up: a base margin for a
  validated analysis, plus an increment for each step away from a
  measured dimension basis, plus an increment for each step away from a
  measured yield basis, plus an increment for the consequence of a
  breakdown, capped by the policy ceiling. The build-up is a declared
  project policy rather than a physical constant, so it is stated with
  the result.
- The build-up is also the business case for measurement: the
  difference between the current requirement and the requirement with
  both bases measured is the margin a coupon campaign or an as-built
  gap measurement would buy back.

## Workflow

1. Declare the three inputs that fix the strategy: the dimension basis,
   the yield basis, and the failure-consequence level. Reject an
   uncategorized value rather than defaulting it, because every
   downstream number depends on this categorization.
2. Resolve the gap the analysis must use. On a measured basis take the
   measurement; on a worst-case basis subtract the tolerance from the
   nominal and reject a tolerance that consumes the gap entirely; on a
   nominal basis take the drawing value and record that the stack is
   outstanding.
3. Resolve the peak secondary-emission yield. On a measured basis take
   the declared curve; on a generic basis demand a bounding family
   value and carry the higher of the two, recording the substitution as
   a finding.
4. Select the strategy the two bases jointly force: a measured-data
   strategy when both are measured, a bounding-envelope strategy when
   either sits at its weakest basis, and a mixed-basis strategy in
   between. Attach the duty each weak basis creates -- stack the
   tolerance, measure the as-built gap, carry a bounding curve, measure
   the production finish.
5. Build up the required multipaction-margin from the policy and report
   the reduction that would follow from moving both bases to measured
   data.
6. Where a predicted breakdown level and an operating level exist,
   compute the achieved multipaction-margin and compare it against the
   requirement; otherwise close with the strategy fixed and the margin
   explicitly not yet demonstrated.

## Pitfalls

- Choosing the margin first and fitting the data basis to it. Clause
  5.3.3.1 runs the other way: the data in hand fixes the strategy, and
  a margin that was picked before the basis was categorized has no
  traceable justification.
- Running the nominal gap as if it were the worst case. The breakdown
  level falls with the gap, so the drawing value is optimistic by the
  whole lower tolerance band, and a result quoted on it understates the
  risk on every unit that builds to the small side.
- Taking a tabulated family yield curve at face value. It is not a
  property of the production surface, and using it without a bounding
  value silently assumes the real finish emits no more strongly than
  the tabulation -- exactly the assumption a contaminated or rough
  surface breaks.
- Treating a surface-measured curve on a coupon as covering a different
  finish or coating. The yield basis follows the surface that was
  measured, so a change of plating, treatment or cleaning state demotes
  the basis and raises the requirement again.
- Comparing the achieved margin with the requirement by bare
  arithmetic. The achieved margin is a difference of logarithms, so a
  case that is exactly on the requirement can land a few units in the
  last place below it; the comparison absorbs that representation error
  while the required margin stays untouched.

## Behavior contract (gate 3)

The basis categorization, gap resolution, bounding-yield substitution,
strategy selection, margin build-up and compliance verdict are
exercised by the gate 3 contract test:
scripts/test_e2001_analysis_margin_strategy.py against
scripts/e2001_analysis_margin_strategy_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_analysis_margin_strategy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
