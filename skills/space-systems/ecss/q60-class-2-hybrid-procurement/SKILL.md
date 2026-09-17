---
name: q60-class-2-hybrid-procurement
description: "Validate that a class 2 hybrid microcircuit is being bought against the specifications ECSS-Q-ST-60C clause 5.6.3 lists for it: read the generic family and the weakest admissible tier from the construction, check the order line cites that family at an issue that has not been superseded and at or above that tier, test the supplier against the qualification register and the month its window closes, grade every die, passive, substrate and interconnect against the tier its kind demands, and take the tier the assembly can actually claim as the weaker of order line and bill of materials. Use when a hybrid purchase order is being raised or reviewed. Trigger: ecss, q-st-60c-clause-5-6-3, class-2-hybrid-purchase, hybrid-generic-specification-family, hybrid-specification-tier-ladder, hybrid-constituent-element-tier, hybrid-supplier-qualification-window."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-2-hybrid-procurement, class-2-hybrid-purchase, hybrid-generic-specification-family, hybrid-specification-tier-ladder, hybrid-constituent-element-tier, hybrid-supplier-qualification-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Hybrid Procurement (space-systems/ecss/q60-class-2-hybrid-procurement)

Use when the task is the clause 5.6.3 purchase of ECSS-Q-ST-60C: a class 2
hybrid microcircuit is being ordered, and the order has to be written against
the specifications the standard lists for that kind of hybrid rather than
against a part number and a promise. The order line is one line. What arrives
under it is a package with a bill of materials inside.

## Domain quick reference

- Construction decides the family. A thick-film build, a thin-film build, a
  multichip module, a microwave hybrid and a substrate assembly are each
  bought against their own generic specification, and citing a neighbouring
  family on the order buys a different set of controls than the one intended.
- A specification claim sits on a ladder, not on a yes or no. A detail
  specification is the strongest rung. A generic specification with a source
  control drawing behind it is next. A maker's own specification referenced
  on the order comes after that, the same specification left unreferenced
  after that, and undocumented is the bottom.
- Class 2 is where the ladder earns its keep. A passive element may ride on a
  maker's own specification provided the order references it, which class 1
  would not accept. An active die does not drop that far under any class.
  Construction moves the floor too: a multichip module or a microwave hybrid
  is ordered at detail-specification strength, a thick-film build is not.
- The assembly cannot claim more than its weakest element. The order line
  tier and the bill of materials tier are two separate claims, and the tier
  the hardware can actually stand behind is the weaker one. Naming the
  element that set it is what makes the claim fixable.
- A cited issue that has been superseded is not a clerical slip. It buys the
  controls of the superseded issue, and nothing in the incoming inspection
  later notices which issue the parts were built to.
- Supplier qualification is a window with a closing month, not a state. An
  order placed in the closing month is inside it; an order placed a month
  later is not, and a qualification closing shortly after the order is worth
  flagging before the build is started rather than after.

## Workflow

1. Read the construction profile: the generic family the order must cite and
   the weakest tier its order line may sit at.
2. Validate the order line: part number, cited family, cited tier, cited
   issue against the current issue, supplier and order month. A cited issue
   ahead of the current one is an input error, not a finding.
3. Raise the citation findings: a family that is not the construction's, an
   issue behind the current one, a tier below the construction's floor.
4. Test the supplier against the qualification register for that family and
   compare the closing month with the order month. Record months remaining
   and whether the order sits inside the warning margin.
5. Validate the bill of materials and reject a repeated element identifier
   before grading anything.
6. Grade each element against the weakest tier its kind is allowed, and roll
   the bill up to the weakest element, naming it.
7. Take the achievable tier as the weaker of the order line tier and the bill
   of materials tier, and take the share of elements meeting their floor.
8. Return one verdict in precedence order: family mismatch, superseded issue,
   order line tier short, supplier qualification lapsed, element tier short,
   otherwise a complete order. Report the achievable tier, the governing
   element, the supplier status and every finding.

## Pitfalls

- Reading the order line tier as the tier of the hardware. The line is a
  claim about the assembly; the bill of materials is what the claim rests on,
  and the weaker of the two is what arrives.
- Accepting a maker's own specification for a die because class 2 accepts one
  for a capacitor. The relaxation is per element kind, and the active devices
  are exactly where it does not apply.
- Citing the generic family without a drawing or detail specification behind
  it. The generic family fixes the method; the layer behind it fixes what
  this particular hybrid has to do.
- Letting a superseded issue stand because the difference looks editorial.
  Nobody downstream re-reads the issue the order cited, and the incoming
  inspection grades against whatever was cited.
- Treating supplier qualification as a badge rather than a window. A
  qualification closing two months after the order will not cover a rebuild,
  a re-screen or a replacement lot.
- Scoring the bill of materials on how many elements pass rather than on
  which one fails. Coverage is a useful number; the governing element is the
  one that has to be fixed for the assembly to claim anything better.

## Behavior contract (gate 3)

The tier ladder, construction profiles, month code parsing and ordering,
order line validation, citation findings, element validation and grading,
bill of materials roll-up, supplier qualification window, tier coverage,
achievable tier and verdict precedence are exercised by the gate 3 contract
test: scripts/test_q60_class_2_hybrid_procurement.py against
scripts/q60_class_2_hybrid_procurement_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_2_hybrid_procurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
