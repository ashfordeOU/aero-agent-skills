---
name: q60-class-2-selection-general-rules
description: "Audit the baseline Class 2 selection rules and how far they reach down the supply chain under clause 5.2.2.1 of ECSS-Q-ST-60C: declare each rule at each tier as applied, met by an accepted equivalent supplier rule, waived against a named approval, or not applied, refuse a chain with a gap in it, downgrade any equivalence or waiver whose evidence is missing, separate a rule never in force in-house from one lost downstream, compute coverage tier by tier, take the weakest tier as the chain's reach, and name the rule surviving fewest tiers. Use when a Class 2 build has to show its selection rules bind its subcontractors too. Trigger: ecss, q-st-60c, q60c2-supply-chain-rule-flow-down, q60c2-rule-survival-depth, q60c2-equivalent-supplier-rule-acceptance, q60c2-flow-down-break."
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
  tags: [ecss, q-st-60c, q-st-60c-eee-class-2-selection-scope, q60-class-2-selection-general-rules, q60c2-baseline-selection-rules, q60c2-supply-chain-rule-flow-down, q60c2-rule-survival-depth, q60c2-equivalent-supplier-rule-acceptance, q60c2-flow-down-break, q60c2-tier-coverage-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Selection General Rules (space-systems/ecss/q60-class-2-selection-general-rules)

Use when the task is the baseline rule set of ECSS-Q-ST-60C clause 5.2.2.1: the
selection rules a Class 2 build applies in-house, and the extension of that same
set to every supplier that chooses a part on the project's behalf.

## Domain quick reference

- Writing the rules and applying them in-house is half the clause. A part chosen
  two tiers down under nobody's rules arrives in the build exactly as if it had
  been chosen under none, so the rule set has to travel with the work.
- The chain is graded on its weakest tier, not on its average. An average lets a
  well-run prime carry a supplier that applies nothing, and the part that fails
  came from that supplier.
- Class 2 admits a form of coverage the stricter classes do not: a supplier's
  own rule, accepted as equivalent, carries the project's rule. That acceptance
  is the whole of the mechanism. An equivalence nobody accepted is a supplier
  doing whatever it already did, described in the project's vocabulary.
- A waiver is coverage only when somebody approved it. Both an unaccepted
  equivalence and an unapproved waiver are the same failure wearing different
  words, and both are worth reporting in their own right as well as through the
  gap they leave, because the gap alone sends the reader to the supplier when
  the missing thing is a signature at home.
- Three situations look alike on a spreadsheet and are not the same. A rule not
  in force in-house is an intention, not a rule, and cannot be required of
  anybody downstream. A rule in force in-house but absent at a tier is a
  flow-down break, the failure this clause exists to catch. A rule genuinely
  covered by an accepted equivalent is neither.
- Reach is contiguous, not a tally. A rule applied in-house, dropped by the
  prime and picked up again by a broker did not survive two tiers; it survived
  none beyond the house, because the part came through the tier that dropped it.
- A chain with a gap in it cannot be graded at all. A tier nobody declared is
  not a tier that applies nothing; it is a tier whose state is unknown, and
  scoring it either way invents an answer.

## Workflow

1. Validate the supply chain: tiers numbered contiguously from the in-house tier
   outward, the in-house tier present, and no gap where an ungraded tier sits.
2. Validate the baseline rule names, then take a state for every rule at every
   tier. An undeclared pair is rejected rather than assumed; silence is not a
   state.
3. Downgrade to not applied any equivalence with no acceptance reference and any
   waiver with no approval reference, and keep what was downgraded so the
   missing record is reported and not just its consequence.
4. Decide which rules are in force by their in-house state alone. A rule not
   applied in-house is reported as that, never as a supplier flow-down break.
5. Compute coverage at each tier over the rules in force only, so a rule the
   project never adopted neither helps nor hurts any supplier's score.
6. Take the weakest tier as the chain's reach, and measure each rule's survival
   depth as the deepest tier it reaches without a break.
7. Name the in-force rule with the shallowest survival as the governing one,
   compare the reach with the required coverage while absorbing representation
   error with a named tolerance, and return one chain verdict with findings
   ranked worst first.

## Pitfalls

- Averaging tier coverage across the chain. The average is the number a prime
  reports and the weakest tier is the number the hardware experiences.
- Counting an unaccepted equivalence or an unapproved waiver as coverage. Both
  are a rule nobody is applying with a note attached, and both read as green on
  a spreadsheet that only looks at the state word.
- Reporting a rule that was never in force in-house as a supplier break. It
  sends the auditor two tiers down to ask about a rule the project itself never
  adopted, and the real fix is at home.
- Counting survival as a tally of covered tiers. A rule dropped at tier one and
  reapplied at tier two protected nothing, because the part passed through tier
  one on its way.
- Scoring a chain with a missing intermediate tier. An undeclared tier is
  unknown, not empty, and filling it in either direction is an invented answer.
- Widening the required coverage so an exactly-met case passes. An equality at
  the boundary is a representation question, handled by the tolerance inside the
  comparison; the required level stays as agreed.

## Behavior contract (gate 3)

The chain contiguity refusal, per-tier state declaration, evidence-driven
downgrade of an equivalence or a waiver, in-force determination from the
in-house tier, coverage over in-force rules only, weakest-tier reach, contiguous
survival depth, governing-rule selection and ranked findings are exercised by
the gate 3 contract test:
`scripts/test_q60_class_2_selection_general_rules.py` against
`scripts/q60_class_2_selection_general_rules_logic.py` (stdlib unittest,
offline). Run:
`python3 scripts/test_q60_class_2_selection_general_rules.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
