---
name: q60-class-3-hybrid-procurement
description: "Evaluate a class 3 hybrid microcircuit purchase against the specifications ECSS-Q-ST-60C clause 6.6.3 lists for it, and cost what the relaxed floor buys back: read the generic family and the nominal tier the construction sets, measure how many rungs below it the order line and each die, passive, substrate and interconnect actually sit, map every shortfall onto the incoming, constructional, burn-in and destructive acceptance steps that compensate it, add the radiation lot verification an active die pulls in, and total the effort against the project cap. Use when a class 3 hybrid order is raised or reviewed. Trigger: ecss, q-st-60c-clause-6-6-3, class-3-hybrid-purchase, hybrid-specification-shortfall-depth, hybrid-compensating-acceptance-plan, hybrid-acceptance-effort-cap, hybrid-supplier-audit-route."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-hybrid-procurement, class-3-hybrid-purchase, hybrid-specification-shortfall-depth, hybrid-compensating-acceptance-plan, hybrid-acceptance-effort-cap, hybrid-supplier-audit-route]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Hybrid Procurement (space-systems/ecss/q60-class-3-hybrid-procurement)

Use when the task is the clause 6.6.3 purchase of ECSS-Q-ST-60C: a class 3
hybrid microcircuit is being ordered against the specifications the standard
lists for its construction. Class 3 lets the specification floor drop further
down the bill of materials than a higher class would, and the drop is the
whole subject. It is not a relaxation that costs nothing — it moves work from
the supplier's qualification onto the purchaser's incoming acceptance, and the
purchase is only real once that work is named and costed.

## Domain quick reference

- Construction still decides the family. A thick-film build, a thin-film
  build, a multichip module, a microwave hybrid and a substrate assembly are
  each bought against their own generic specification, and a neighbouring
  family on the order buys a different set of controls than the one intended.
- The nominal tier is a starting point at class 3, not a floor to be passed or
  failed. What matters is the depth: how many rungs below its nominal tier the
  claim sits, because the depth is what sizes the acceptance work.
- Depth is not linear in name only. One rung down is an incoming electrical
  test. Two is that test plus a constructional analysis and an extended
  burn-in, because a maker's unreferenced specification says nothing about how
  the part was built. Three brings destructive physical analysis and lot
  homogeneity in with them.
- One rung is unbounded and it is the last one. A part with no documentation
  at all cannot be compensated, because the acceptance procedure has nothing
  to be written against and no criterion to pass. That is a refusal, not a
  deeper plan.
- An active die is not a passive with more terminals. A die that dropped below
  its nominal tier pulls radiation lot verification in on top of everything
  the depth map asked for, because no amount of electrical screening sees a
  radiation response.
- The acceptance plan is a union, not a sum. Two elements one rung down need
  the incoming test once, and costing it twice makes a purchase look
  unaffordable that is not.
- Supplier assessment has two routes at class 3. A register entry for that
  family is one. A supplier audit whose reference is named and still inside
  its validity is the other, and an audit nobody can date is neither.

## Workflow

1. Read the construction profile: the generic family the order must cite and
   the nominal tier a class 3 order line sits at.
2. Validate the order line and the bill of materials, rejecting a repeated
   element identifier before anything is graded.
3. Measure the shortfall depth of the order line and of every element against
   the nominal tier its kind carries.
4. Map each depth onto its acceptance steps, add the radiation lot
   verification any active element in shortfall pulls in, and take the union
   as the acceptance plan.
5. Total the plan's effort and compare it with the cap the project set,
   reporting the ratio rather than a bare pass.
6. Test the supplier on both routes: the register for that family first, then
   an audit record inside its validity.
7. Return one verdict in precedence order: an undocumented order line or
   element, then a family mismatch, then an unassessed supplier, then a burden
   over the cap, otherwise a purchase as specified or a purchase with the
   named compensating acceptance plan attached.

## Pitfalls

- Reading class 3 as permission to buy anything. The floor drops by rungs that
  each have a price, and the bottom rung is not on the ladder at all.
- Grading the bill of materials pass or fail against the nominal tier. A
  pass/fail answer hides the only number the buyer needs, which is how much
  acceptance work this particular shortfall costs.
- Costing the acceptance plan element by element. Steps overlap, the plan is a
  union, and a per-element sum inflates a purchase that the project could
  actually carry.
- Screening an underspecified die electrically and calling it covered. The
  electrical test finds what the electrical test finds; the radiation response
  of an unqualified lot is not in it.
- Treating a supplier audit as a formality that unlocks any supplier. The
  audit is an assessment with a date on it, and one nobody can point to by
  reference is the same as no assessment.
- Letting the acceptance plan grow past the cap and calling it a schedule
  problem. The cap is what makes the relaxed floor an engineering decision
  rather than a deferral, and a plan above it is a purchase whose real cost
  was never accepted.

## Behavior contract (gate 3)

The tier ladder, shortfall depth, construction profiles, policy merge, order
line and element validation, depth-to-step compensation map, active element
extra steps, acceptance plan union, effort total, burden ratio, two-route
supplier assessment, unbounded element detection and verdict precedence are
exercised by the gate 3 contract test:
scripts/test_q60_class_3_hybrid_procurement.py against
scripts/q60_class_3_hybrid_procurement_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_3_hybrid_procurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
