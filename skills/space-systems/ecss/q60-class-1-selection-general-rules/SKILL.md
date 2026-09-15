---
name: q60-class-1-selection-general-rules
description: "Audit the baseline Class 1 selection rules and how far they reach down the supply chain under ECSS-Q-ST-60C clause 4.2.2.1: declare each rule as applied, waived against a named approval, or not applied at every tier from in-house outward, refuse a chain with a gap in it, compute coverage tier by tier, take the weakest tier as the chain's reach, separate a rule missing in-house from one lost downstream, and name the rule surviving fewest tiers. Use when a Class 1 build has to show its selection rules bind its subcontractors too. Trigger: ecss, q-st-60c-eee-selection-scope, class-1-baseline-selection-rules, class-1-supply-chain-rule-flow-down, class-1-flow-down-break, supplier-tier-rule-coverage, class-1-selection-rule-waiver-approval."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q60-class-1-selection-general-rules, class-1-baseline-selection-rules, class-1-supply-chain-rule-flow-down, class-1-flow-down-break, supplier-tier-rule-coverage, class-1-selection-rule-waiver-approval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Selection General Rules (space-systems/ecss/q60-class-1-selection-general-rules)

Use when the task is the baseline rule set of ECSS-Q-ST-60C clause
4.2.2.1 -- the selection rules a Class 1 build applies in-house, and
the extension of that same set to every supplier that chooses a part on
the project's behalf.

## Domain quick reference

- Writing the rules and applying them in-house is half the clause. A
  part chosen two tiers down under nobody's rules arrives in the build
  exactly as if it had been chosen under none, so the rule set has to
  travel with the work.
- The chain is graded on its weakest tier, not on its average. An
  average lets a well-run prime carry a supplier that applies nothing,
  and the part that fails came from that supplier.
- Three situations look alike on a spreadsheet and are not the same. A
  rule not in force in-house is an intention, not a rule, and cannot be
  required of anybody downstream. A rule in force in-house but absent
  at a tier is a flow-down break -- the failure this clause exists to
  catch. A rule waived at a tier counts only when the waiver names the
  approval behind it.
- A waiver with no named approval is a rule that was simply not
  applied, written in nicer language. Requiring the reference is what
  keeps the distinction real.
- The chain has to run without a gap. Declaring what a tier-2 supplier
  does while saying nothing about the tier-1 subcontractor between the
  two describes a chain nobody can follow, so the gap is rejected.
- Two outputs matter beyond the verdict: the tier that governs the
  chain's reach, and the rule that survives the fewest tiers. The first
  says where to send the auditor, the second says which rule the chain
  is quietly dropping everywhere.

## Workflow

1. Name the programme and declare, for every tier from in-house
   outward, the status of each baseline rule. A tier that leaves a rule
   undeclared is rejected; an absent status is not a status.
2. Reject a chain with no in-house tier -- there is no baseline to
   extend -- and reject a chain with a gap between declared tiers.
3. Require an approval reference on every waiver. Without one the rule
   counts as not applied.
4. Compute coverage tier by tier, then take the minimum as the chain's
   reach. Do not average.
5. Separate the rules not in force in-house from the rules lost at a
   supplier tier, and report each with the tier it breaks at.
6. Close with the verdict, the governing tier, the chain coverage
   against the target, and the rule surviving fewest tiers.

## Pitfalls

- Averaging tier coverage. The average hides the one supplier applying
  nothing, and that supplier is the one the failed part came from.
- Counting an unapproved waiver as coverage. A waiver is a decision
  somebody signed; without the reference it is an omission wearing a
  waiver's name.
- Reporting a rule absent in-house as a flow-down break. Nothing flowed
  down, because nothing was in force to flow; calling it a break sends
  the auditor to the supplier instead of to the project.
- Grading only the tiers that answered. An undeclared tier is not a
  compliant tier, and a chain with a gap in the middle cannot be scored
  at all -- it has to be completed first.
- Comparing coverage with a target by bare arithmetic. Coverage is a
  quotient of two counts and a target is a decimal literal, so a
  coverage built to sit exactly on a target can land a few units in the
  last place below it; the comparison absorbs that while the target
  stays untouched.

## Behavior contract (gate 3)

The rule-entry validation, waiver approval requirement, chain structure
and gap rejection, per-tier coverage, weakest-tier reach, governing
tier, flow-down break detection, unenforceable-rule separation,
weakest-rule selection and overall verdict are exercised by the gate 3
contract test: scripts/test_q60_class_1_selection_general_rules.py
against scripts/q60_class_1_selection_general_rules_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_selection_general_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
