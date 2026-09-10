---
name: e10-budget-margin-policy
description: "Use when consolidating technical budgets (mass, power, data rate, pointing, thermal, propellant, etc.) at system level under ECSS-E-ST-10C flow-down and applying the project margin policy: roll up contributor current-best-estimate plus maturity margin, add the system-level contingency margin, and check the result against the allocated value with a phase-appropriate minimum remaining margin. Trigger: ecss, e-st-10c, technical budget, budget consolidation, margin policy, mass budget, power budget, data rate budget, link budget, contingency margin, maturity margin, system margin."
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
  tags: [ecss, e-st-10c, technical-budget, margin-policy, mass-budget, power-budget, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Budget Consolidation and Margin Policy (space-systems/ecss/e10-budget-margin-policy)

Use when the task is consolidating technical budgets at system level and
applying the project margin policy under ECSS-E-ST-10C clause 5.6.6.

## Domain quick reference

- ECSS-E-ST-10C clause 5.6.6 requires the system engineering function to
  consolidate technical budgets (mass, power, data rate, pointing,
  thermal, propellant, etc.) at system level from the contributions of
  every product, and to apply the project margin policy to the result.
- Each contributor reports a current best estimate (CBE) plus a
  maturity margin (a percentage reflecting how mature its design is);
  CBE x (1 + maturity margin) gives the contributor's predicted value.
  Predicted values are summed across contributors to consolidate a
  budget category at system level.
- A system-level contingency margin is then applied on top of the
  consolidated predicted total, and the result is checked against the
  allocated (requirement) value for that category.
- Margin policy also sets a minimum remaining margin (percentage of
  the allocated value) required at each lifecycle phase; the required
  minimum shrinks as the design matures from phase A through E,
  consistent with the phase model in the sibling systems-engineering
  leaf.
- This leaf scopes system-level consolidation and margin-policy
  compliance only. Applying budget/margin policy while designing a
  single product (allocation, consumption tracking within that
  product) is the sibling e10-design-budgets leaf (10C clause
  5.4.1.2); generating or validating the Technical Budget document per
  the DRD is the sibling e10-budget-drd leaf (10C Annex I).

## Workflow

1. For each contributor to a budget category, record its CBE and
   maturity margin percentage; compute its predicted value.
2. Consolidate the category at system level by summing every
   contributor's predicted value.
3. Apply the system-level contingency margin on top of the
   consolidated predicted total.
4. Check the margined total against the allocated (requirement) value
   for the category: compute remaining margin and remaining margin
   percentage, and flag whether the budget is within or has exceeded
   its allocation.
5. Compare the remaining margin percentage against the minimum
   required for the current lifecycle phase; the category is
   margin-policy compliant only if it is within budget and meets or
   exceeds that minimum.
6. Roll up every category's compliance into a system budget report;
   any non-compliant category must be resolved (re-budgeted, or the
   allocation renegotiated) before the phase's review gate.

## Pitfalls

- Summing raw CBE values across contributors instead of predicted
  values (CBE with maturity margin applied) — this understates the
  consolidated budget.
- Checking the consolidated predicted total against the allocation
  without first applying the system-level contingency margin.
- Declaring a category "ready" for a review gate because it is within
  budget, without checking that the remaining margin also meets the
  phase-appropriate minimum (a budget can be within allocation yet
  still carry too little margin for its phase).
- Confusing this leaf's system-level consolidation and margin-policy
  check with product-level budget/margin application during design
  (e10-design-budgets, 10C 5.4.1.2) or with generating the Technical
  Budget document itself (e10-budget-drd, 10C Annex I).

## Behavior contract (gate 3)

The contribution, consolidation, system-margin, allocation-check, and
phase-compliance logic is exercised by the gate 3 contract test:
scripts/test_e10_budget_margin_policy.py against
scripts/e10_budget_margin_policy_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_budget_margin_policy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
