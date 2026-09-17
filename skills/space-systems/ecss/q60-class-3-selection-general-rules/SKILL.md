---
name: q60-class-3-selection-general-rules
description: "Audit the baseline Class 3 selection rules and how far they reach down the supply chain under ECSS-Q-ST-60C clause 6.2.2.1: declare each rule at every tier from in-house outward as evidenced, supplier-declared only, waived against a named approval or not applied, give a bare declaration half credit, refuse a waiver or a not-applicable raised against a binding rule, weight the rules, compute coverage tier by tier, take the weakest tier as the chain's reach, separate a rule missing in-house from one lost downstream, and name the rule surviving fewest tiers. Use when a Class 3 build has to show its selection rules still bind the suppliers that buy for it. Trigger: ecss, q-st-60c, q60-c3-baseline-selection-rules, q60-c3-supply-chain-rule-flow-down, q60-c3-flow-down-break, q60-c3-supplier-declaration-half-credit, q60-c3-binding-rule-waiver-refusal."
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
  tags: [ecss, q-st-60c, q60-class-3-selection-general-rules, q60-c3-baseline-selection-rules, q60-c3-supply-chain-rule-flow-down, q60-c3-flow-down-break, q60-c3-supplier-declaration-half-credit, q60-c3-binding-rule-waiver-refusal, q60-c3-tier-rule-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Selection General Rules (space-systems/ecss/q60-class-3-selection-general-rules)

Use when the task is the baseline rule set of ECSS-Q-ST-60C clause
6.2.2.1 -- the selection rules a Class 3 build applies in-house, and
the extension of that same set to every supplier that chooses a part on
the project's behalf.

## Domain quick reference

- Writing the rules and applying them in-house is half the clause. The
  other half is that the same set still binds wherever somebody else
  picks the part: a subcontractor building an equipment, a supplier
  buying to its own catalogue, a distributor substituting a line item.
  A rule that stops at the project fence is a rule the parts in the
  flight build were never chosen against.
- Class 3 is the class where the chain is longest and the evidence is
  thinnest, so the distinction that matters is not applied against not
  applied. It is applied with evidence against merely declared. A
  supplier that says it screens finishes and a supplier that shows a
  finish certificate are not in the same state, and collapsing them is
  how a chain reads green while half of it rests on assertions. A bare
  declaration earns partial credit, never full credit.
- Two claims are refused outright on a binding rule: a waiver, however
  well approved, and a not-applicable. A binding rule is one the class
  itself rests on, so if it can be waived at a distributor it was never
  binding. On a non-binding rule both claims are admissible -- a waiver
  against a named approval, and a not-applicable against a recorded
  justification, because a distributor genuinely does not set an
  operating point.
- An undeclared rule is open, not absent. A ledger silently missing an
  entry reads as clean exactly where nobody looked, so a missing entry
  stays in the denominator at zero credit.
- The chain is only as long as its weakest tier, so the reach of the
  rule set is the lowest tier coverage and never the average. An
  average lets three strong tiers carry a distributor that applies
  nothing.
- The useful outputs are that reach, the tier that sets it, the rule
  surviving fewest tiers, and the separation of a rule missing in-house
  from one lost downstream -- the first is a project defect, the second
  is a flow-down defect, and different people fix them.

## Workflow

1. Name the project and declare the tiers that actually touch the part
   choice. The in-house tier is required; a chain that starts at a
   supplier has no baseline to extend.
2. Expand the declaration so every rule exists at every declared tier.
   Anything the project did not mention becomes undeclared rather than
   disappearing.
3. Grade each entry. Evidence earns full credit, a bare supplier
   declaration earns half, an approved waiver on a non-binding rule
   earns full, a justified not-applicable leaves the denominator, and
   everything else earns nothing.
4. Refuse a waiver or a not-applicable raised against a binding rule.
   Both keep their place in the denominator at zero credit and are
   reported as claims to withdraw.
5. Compute weighted coverage tier by tier, then take the weakest tier
   as the chain's reach and compare it with the floor.
6. Split the shortfalls: rules never carried in-house, rules carried
   in-house and lost below, and the single rule surviving fewest tiers.
7. Close with the verdict, the governing tier and one action per
   finding.

## Pitfalls

- Averaging coverage across tiers. The average is dominated by the
  tiers the project controls, which is precisely where the rule set was
  never at risk; the reach is the minimum.
- Reading a supplier's declaration as application. The declaration is
  the promise, not the evidence, and a chain scored on promises is
  green until the first parts arrive.
- Letting a binding rule be waived because the approval looks solid. An
  approval makes a waiver traceable, not admissible; the rules the
  class rests on have no waiver route at any tier.
- Accepting an unjustified not-applicable. Without a recorded reason it
  is indistinguishable from nobody having looked, so it stays open and
  stays counted.
- Treating a rule missing in-house as a flow-down failure. There was
  nothing to flow down; chasing the supplier for it wastes the fix on
  the wrong party.
- Comparing the weighted coverage with its floor by bare arithmetic.
  Coverage is a quotient while the floor is a decimal literal, so a
  declaration built to sit exactly on the floor can land a few units in
  the last place under it; the comparison absorbs that while the floor
  stays untouched.

## Behavior contract (gate 3)

The rule table and binding set, entry grading with partial credit for a
bare declaration, waiver and not-applicable admissibility, chain
expansion with undeclared defaults, weighted tier coverage, the weakest
tier as the chain's reach, in-house gaps against flow-down breaks, the
weakest rule and the overall verdict are exercised by the gate 3
contract test:
scripts/test_q60_class_3_selection_general_rules.py against
scripts/q60_class_3_selection_general_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_selection_general_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
