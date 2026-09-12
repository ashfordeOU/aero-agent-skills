---
name: e20-electrical-budgets-and-margin-policy
description: "Use when compute an electrical technical budget and evaluate it against the margin policy that ECSS-E-ST-20C clause 4.2.2.2 inherits from the general engineering standard: categorize the budget into its power, signal or physical domain, apply the maturity-based contingency to each equipment line item without double counting a contingency already folded into its nominal value, roll the duty-cycled line items up into a per-mode demand, select the worst-case mission mode, add the project-phase system margin on top, and compare the declared capability against that demand to report the achieved margin and the shortfall. Trigger: ecss, e-st-20-electrical-scope, electrical-power-budget, design-maturity-contingency, project-phase-system-margin, worst-case-mode-demand, harness-voltage-drop-budget, data-bus-bandwidth-budget, e-st-10c-margin-policy-linkage."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electrical-budgets-and-margin-policy, electrical-power-budget, design-maturity-contingency, project-phase-system-margin, worst-case-mode-demand, harness-voltage-drop-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Budgets and Margin Policy (space-systems/ecss/e20-electrical-budgets-and-margin-policy)

Use when the task is the electrical technical budget of ECSS-E-ST-20C
clause 4.2.2.2 -- taking the margin and budget rules the general
engineering standard defines for the project as a whole and applying
them to an electrical quantity: power, energy, current, voltage drop,
bus bandwidth, harness mass.

## Domain quick reference

- Clause 4.2.2.2 does not invent an electrical margin policy. It binds
  electrical design to the project-level rules of the general
  engineering standard, so the question is never "what margin feels
  right for this converter" but "what does the project margin policy
  require at this phase, for equipment of this maturity". The leaf's
  job is to apply that policy mechanically and to expose where a
  budget was built by a different rule.
- Margin arrives at two distinct levels and they are not the same
  thing. Item-level *contingency* covers uncertainty in one equipment's
  own consumption and is set by that equipment's maturity: a
  flight-measured unit carries none, a qualified off-the-shelf unit a
  little, a modified design more, a new development the most.
  System-level *margin* covers the integration-level unknowns and is
  set by the project phase, shrinking as the design matures towards
  flight. Both apply, in that order: contingency first on each item,
  system margin afterwards on the rolled-up total.
- Line items are duty-cycled before they are summed. An equipment that
  draws its nominal power for a quarter of a mode contributes a
  quarter of that power to the mode's average demand. Duty cycle is a
  fraction in the closed interval zero to one; anything outside it is
  an input error, not a conservative assumption.
- The budget is sized on the worst-case mission mode, not on an
  average across modes. Each mode is rolled up independently and the
  largest demand drives the required capability. A budget that averages
  across modes hides the mode that actually sets the hardware.
- Achieved margin is the fraction by which declared capability exceeds
  demand, expressed as a fraction of demand. It is compared against
  the policy-required margin; a budget whose achieved margin falls
  below the requirement reports both the margin and the absolute
  shortfall, because the recovery action depends on the size of the
  gap, not on the fact of the breach.

## Workflow

1. Categorize the budget into its domain -- power, signal or physical.
   Reject an unrecognized budget type before any number is computed.
2. For each line item, resolve its contingency from its maturity, and
   check whether its nominal value already carries contingency inside
   it. Apply the maturity contingency only where it does not.
3. Multiply each item by its duty cycle in the mode under evaluation
   and sum, giving the mode's contingency-loaded demand.
4. Repeat per mode and select the worst case; carry the mode name
   alongside the number so the driving mode is visible downstream.
5. Apply the project-phase system margin to the worst-case demand.
   That product is the capability the design must provide.
6. Compare the declared capability against the required capability and
   report the achieved margin against the policy-required margin,
   together with the absolute shortfall when it is short.
7. For a voltage-drop budget, compute the drop from harness resistance
   and load current and compare it against the allowable fraction of
   the bus voltage; a drop within the allowance still consumes budget
   and must be reported, not silently absorbed.

## Pitfalls

- Counting the same uncertainty twice: applying a maturity contingency
  to a line item whose nominal value was already delivered with
  contingency folded in. The two are indistinguishable once summed, so
  the conflicting declaration is flagged at the item, not reconciled.
- Applying the system margin to each item instead of to the rolled-up
  total -- mathematically the same only when every item carries the
  same contingency, and misleading in every other case because it
  hides which level the margin came from.
- Sizing on an averaged demand across mission modes. The worst-case
  mode sets the hardware; an average across modes understates it and
  the error grows with the spread between modes.
- Carrying the early-phase margin unchanged to the end of the project,
  or dropping to the late-phase margin while equipment is still new
  development. Phase sets the system margin, maturity sets the item
  contingency, and neither substitutes for the other.
- Reading a positive achieved margin as compliance without checking it
  against the policy requirement -- any surplus at all looks like a
  pass, and the policy floor is what the review actually grades.

## Behavior contract (gate 3)

The budget categorization, maturity contingency, duty-cycled roll-up,
worst-case mode selection, phase system margin, achieved-margin and
voltage-drop logic is exercised by the gate 3 contract test:
scripts/test_e20_electrical_budgets_and_margin_policy.py against
scripts/e20_electrical_budgets_and_margin_policy_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_electrical_budgets_and_margin_policy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
