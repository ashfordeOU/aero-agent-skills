---
name: e2001-single-carrier-analysis-margins
description: "Use when derive the nominal analysis-margin of ECSS-E-ST-20-01C clause 4.6.2.2 for single-carrier operation: start from the base value owed by the selected design-analysis-level, add a contribution for every uncertainty the worst-case model does not already bound - manufacturing-tolerance spread, secondary-emission-yield scatter, electromagnetic-field-model error, power-measurement uncertainty and temperature-induced gap change - add the equipment-type adder, subtract the design-heritage credit only when the recurring unit keeps the same manufacturing route, hold the result at the declared floor, then compare it against the achieved decibel multipactor-margin and report the shortfall. Trigger: ecss, e-st-20-electrical-scope, single-carrier-multipactor, nominal-analysis-margin, margin-contribution-budget, equipment-type-adder, design-heritage-credit, secondary-emission-yield-scatter, multipactor-margin-shortfall."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-single-carrier-analysis-margins, single-carrier-multipactor, nominal-analysis-margin, margin-contribution-budget, equipment-type-adder, design-heritage-credit, secondary-emission-yield-scatter]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Single-Carrier Nominal Analysis Margins (space-systems/ecss/e2001-single-carrier-analysis-margins)

Use when the task is the nominal analysis-margin of ECSS-E-ST-20-01C
clause 4.6.2.2 -- building, for a single-carrier case closed by
modelling, the decibel figure the unit owes, out of the base value of
the chosen design-analysis-level, the uncertainty contributions the
model does not already bound, the equipment-type adder and the credit a
qualified recurring design has earned.

## Domain quick reference

- The required analysis-margin is assembled, not looked up. Its base
  is set by the design-analysis-level: the chart route carries the
  larger base because it reads a generic curve, the detailed
  numerical-modelling route carries a smaller one because it models
  the actual geometry and surface. On top of that base sit the
  uncertainty contributions.
- Five contributions are budgeted case by case: manufacturing-tolerance
  spread on the electrode separation, secondary-emission-yield scatter
  between the datasheet surface and the flight surface,
  electromagnetic-field-model error in the predicted gap field,
  radio-frequency power-measurement uncertainty at the interface, and
  temperature-induced gap change across the qualification range. A
  contribution already bounded by an explicit worst-case run drops out
  of the budget; one that is not bounded contributes its adder.
- A coverage claim is only as good as the route that supports it. The
  chart route cannot bound field-model error or yield scatter by
  construction, so such a claim is rejected at level one and the adder
  is retained -- silently accepting it is how a unit ends up with a
  paper margin it never had.
- The equipment-type adder reflects how much of the gap is controlled
  by assembly rather than by machining: a sealed waveguide run is the
  reference, while connectorised interfaces, radiating elements and
  active output stages each carry more. Design heritage works the
  other way, returning credit for a qualified recurring design -- but
  only while the manufacturing route is unchanged, since the credit
  rests on the flown hardware being reproduced, not merely on the
  drawing being reused.
- The assembled figure is then held at a declared floor. The floor
  exists so no accumulation of credits can drive the requirement below
  the point where the gap is still covered against the uncertainties
  nobody bounded.

## Workflow

1. Fix the design-analysis-level of the case and take its base value
   from the declared margin-policy table. An unknown level is a
   rejection, not a default.
2. For each of the five contributions, record whether an explicit
   worst-case run bounds it. Every contribution needs a statement --
   a silent omission is a rejection, because an unstated contribution
   is indistinguishable from a forgotten one.
3. Drop the adder of each bounded contribution; reject a coverage
   claim the level cannot support, retain that adder and raise a
   finding against the claim.
4. Add the equipment-type adder for the hardware category, then
   subtract the heritage credit -- withholding it, with a finding,
   when the recurring design does not keep the same manufacturing
   route.
5. Hold the assembled figure at the declared floor and record whether
   the floor bound the result, so a reviewer sees which cases are
   floor-driven rather than contribution-driven.
6. Compute the achieved decibel multipactor-margin from the gap's
   multipactor-threshold-power and its highest operating carrier-power,
   compare, and report the shortfall. The comparison runs to a declared
   representation tolerance so a case sitting exactly on its
   requirement, where the requirement is a sum of adders and the
   achieved value a logarithm, reads as met rather than as a few units
   in the last place short.

## Pitfalls

- Reusing a margin figure from a sister unit. The figure is built from
  this case's coverage statements, equipment category and heritage; a
  copied number hides which contributions were never bounded.
- Claiming worst-case coverage of yield scatter or field-model error
  on the chart route. That route has no model to run worst cases in,
  so the claim cannot be substantiated and the adder stands.
- Taking heritage credit for a design whose manufacturing route,
  plating line or surface treatment changed. Multipactor behaviour
  follows the real surface, and a new route is a new surface.
- Letting credits drive the requirement below the declared floor, or
  re-deriving the floor per case. The floor is a policy value, applied
  after the assembly, and a floor-driven case is reported as such.
- Comparing an achieved margin against the base value instead of the
  assembled requirement -- the base is the starting point of the
  budget, never the requirement itself.

## Behavior contract (gate 3)

The base lookup, contribution budget with coverage-claim rejection,
equipment-type adder, heritage credit with the manufacturing-route
condition, floor application and shortfall comparison are exercised by
the gate 3 contract test:
scripts/test_e2001_single_carrier_analysis_margins.py against
scripts/e2001_single_carrier_analysis_margins_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_single_carrier_analysis_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
