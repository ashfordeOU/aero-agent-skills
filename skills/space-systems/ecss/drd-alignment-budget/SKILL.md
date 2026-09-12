---
name: drd-alignment-budget
description: "Use when determine the structural alignment budget for a spacecraft or instrument mounting interface under ECSS-E-ST-32C Annex L: identify every contributor to alignment error — manufacturing tolerances, thermoelastic distortion, gravity-release deformation, load-induced deflection, and measurement uncertainty — assign sensitivity coefficients, combine contributions by root-sum-square or worst-case arithmetic, and verify the resulting total against the pointing or interface alignment requirement. The budget must cover both on-ground and on-orbit alignment states and record each contributor's type, magnitude, and sensitivity coefficient. Flag any exceedance or missing allowable before closing the budget. Trigger: ecss, e-st-32c, e-st-32-structures-scope, alignment-budget, structural-alignment, thermoelastic, gravity-release, pointing-budget, interface-alignment."
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
  tags: [ecss, e-st-32c, e-st-32-structures-scope, alignment-budget, structural-alignment, thermoelastic, gravity-release, pointing-budget, interface-alignment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — DRD Alignment Budget (space-systems/ecss/drd-alignment-budget)

Use when the task is to determine and verify the structural alignment budget
for a spacecraft or instrument mounting interface, following ECSS-E-ST-32C
Annex L. The budget accounts for all sources of angular or linear misalignment
and checks the total against a specified pointing or interface requirement.

## Domain quick reference

- The structural alignment budget (SAB) aggregates every contributor that
  shifts a physical reference frame away from its nominal position. ECSS-E-ST-32C
  Annex L requires the budget to account for five canonical contributor types:
  manufacturing tolerances (dimensional variation from production), thermoelastic
  distortion (temperature-induced deformation between on-ground and on-orbit thermal
  states), gravity-release deformation (shape change between the 1-g ground state
  and the 0-g on-orbit state), load-induced deflection (quasi-static deformation
  under design limit loads), and measurement uncertainty (metrological error in
  alignment measurements and surveys).
- Each contributor is assigned a sensitivity coefficient that converts the raw
  magnitude into an effective error at the reference interface. A coefficient
  of 1.0 means the error propagates without amplification; values above 1.0
  indicate a mechanical amplification path.
- Contributions are combined by one of two methods: root-sum-square (RSS)
  treats contributors as statistically independent and random — the method
  is appropriate when sources are uncorrelated; worst-case arithmetic sums
  absolute values and is appropriate when contributors are systematic or
  when correlation cannot be demonstrated. Mixing methods within the same
  budget level is not permitted.
- Every alignment-critical interface must carry an explicit allowable value
  derived from the pointing or interface requirement. A budget without a
  recorded allowable is not assessable; this is itself a finding, not a pass.

## Workflow

1. Identify every interface or pointing reference to be budgeted. For each
   interface, record the applicable requirement (pointing accuracy, alignment
   tolerance) that drives the allowable error.
2. For each interface, enumerate all contributor types that apply. Each contributor
   is recorded with its type (one of the five canonical types), raw magnitude,
   and sensitivity coefficient. Reject any contributor whose type is not
   recognized before it enters the budget.
3. Compute the effective error for each contributor by multiplying its raw
   magnitude by its sensitivity coefficient.
4. Combine all effective errors at the interface using the selected method:
   RSS for independent random contributors, or worst-case arithmetic for
   systematic or correlated contributors. Document the method choice and its
   justification.
5. Compare the combined total against the interface allowable. Record the
   result as compliant (total does not exceed allowable), exceeded (total
   exceeds allowable — record the exceedance margin), or missing-budget
   (no allowable is on record — flag as an open finding).
6. Repeat for every alignment-critical interface. The budget is closed only
   when every interface is compliant and all allowables are on record.

## Pitfalls

- Omitting the sensitivity coefficient step and applying raw contributor
  magnitudes directly as effective errors — a contributor routed through a
  mechanical lever or kinematic amplification path deposits a larger error
  at the reference than its measured magnitude, and ignoring the coefficient
  understates the total.
- Mixing RSS and worst-case arithmetic within a single interface budget
  without documented justification — selecting the more conservative method
  for some contributors and the less conservative for others is not
  permitted; the method must be applied uniformly or split into clearly
  separate sub-budgets with explicit combination at the top level.
- Treating a missing allowable as a compliant result — an interface without
  a recorded allowable has not been assessed against any requirement; it
  must be flagged as an open finding and resolved before the budget is closed.
- Computing the budget only for the on-orbit thermal state and ignoring the
  on-ground (pre-launch) state — alignment surveys and acceptance tests are
  performed on the ground, and the gravity-release and thermoelastic
  contributors must be shown to be within allowable in both states.

## Behavior contract (gate 3)

The contributor-categorization, sensitivity-application, RSS-combination,
worst-case-combination, and budget-check logic is exercised by the gate 3
contract test: scripts/test_drd_alignment_budget.py against
scripts/drd_alignment_budget_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_drd_alignment_budget.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
