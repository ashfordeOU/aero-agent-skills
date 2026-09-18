---
name: q6012-design-iteration-count
description: "Size the development cycles an MMIC design plans before its freeze. Use when ECSS-Q-ST-60-12C clause 7.1.3 asks how many iterations the effort carries: derive the per-cycle convergence factor from process-model maturity, compute the cycles that close the predicted-to-required performance gap down to the acceptance gap, raise that to the novelty floor a heritage, derivative or new design carries, divide the schedule left after the non-recurring front-end by the foundry turnaround to get what the plan can actually run, then compare the planned count against both and report the residual gap. Refuses a non-contracting factor. Trigger: ecss, q-st-60-12c-clause-7-1-3, mmic-design-iteration-count, mmic-design-cycle-planning, mmic-gap-convergence-factor, mmic-novelty-iteration-floor, foundry-cycle-schedule-capacity, mmic-design-freeze-readiness."
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
  tags: [ecss, q-st-60-12-mmic-design-scope, q6012-design-iteration-count, mmic-design-cycle-planning, mmic-gap-convergence-factor, mmic-novelty-iteration-floor, foundry-cycle-schedule-capacity, mmic-design-freeze-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC Design — Planned Iteration Count (space-systems/ecss/q6012-design-iteration-count)

Use when the task is the design-iteration branch of ECSS-Q-ST-60-12C
clause 7.1.3 — settling how many development cycles a microwave circuit
design plans to run before it is frozen, and whether the plan on the
table is that number.

## Domain quick reference

- A development cycle is a foundry run plus its evaluation, so the count
  is a whole number and the answer is never "1.6 cycles". Rounding is up
  to the next whole cycle, because a fraction of a run buys nothing.
- How fast a cycle closes the gap between predicted and required
  performance follows the maturity of the models the prediction was made
  with. A model calibrated on measured hardware from the same process
  leaves a small share of the gap standing after a cycle; a vendor
  default or an extrapolated model leaves much more, because part of
  what the cycle measured was model error rather than design error. The
  same gap therefore needs more cycles on a weaker model.
- The analytic closure count is a floor on the physics, not on the
  programme. Novelty puts its own floor underneath it: a design reusing
  a qualified cell set can converge in one cycle, a derivative needs
  two, and a new circuit on a new process is not frozen on fewer than
  three however close the first prediction looks. The required count is
  the larger of the two floors, never their average.
- A gap ratio that is an exact power of the convergence factor lands on
  a whole number that log arithmetic can place a few ULP above it, which
  would silently add a spare cycle to every such plan. The rounding
  absorbs that with a named tolerance rather than by padding.
- Schedule capacity is a separate quantity from the required count and
  they disagree often. The weeks left after the non-recurring front-end
  work, divided by the turnaround of one cycle, give what the programme
  can physically run. A plan can be correct against the physics and
  still be undeliverable against the calendar, and the two findings are
  reported separately because they have different owners.
- The residual gap the planned cycles actually reach is reported
  alongside the counts. A plan that meets the required count but leaves
  a gap outside the acceptance gap has a arithmetic problem somewhere in
  its inputs, and the residual is what exposes it.

## Workflow

1. Validate the inputs: a non-negative initial gap, a strictly positive
   acceptance gap, a known model-maturity token, a known novelty
   category, a non-negative whole planned-cycle count, and a positive
   cycle turnaround.
2. Map the model maturity onto its per-cycle convergence factor. A
   factor at or above one never converges and is an input error, not a
   slow case.
3. Compute the closure count from the geometric contraction of the gap,
   rounding up to the next whole cycle with the representation tolerance
   applied first. An initial gap already inside acceptance needs none.
4. Take the novelty floor for the design category and set the required
   count to the larger of the closure count and that floor. Record which
   of the two drove it, because the two are fixed by different people.
5. Compute schedule capacity from the weeks remaining after the
   non-recurring front-end, divided by the cycle turnaround and rounded
   down with the same tolerance, so a schedule that fits an exact whole
   number of cycles is not short-changed one.
6. Compute the residual gap the planned cycle count actually reaches and
   compare it with the acceptance gap, absorbing an exact equality with
   the tolerance rather than by relaxing acceptance.
7. Report freeze support only when the plan meets the required count,
   the schedule can carry the plan, and the residual gap is inside
   acceptance; otherwise return the shortfall, schedule and residual
   findings separately.

## Pitfalls

- Planning the cycle count from the schedule and calling it the
  requirement. Capacity says what can be run, not what has to be; a plan
  cut to fit the calendar is a schedule finding, not a smaller required
  count.
- Averaging the analytic closure count and the novelty floor. Both are
  floors, so the requirement is the larger; averaging them produces a
  number that satisfies neither.
- Freezing a new design on one cycle because the first prediction landed
  close. The floor exists because the first prediction on an
  uncalibrated process is the least trustworthy number in the effort.
- Reusing a convergence factor from a different process or model
  vintage. The factor is a property of the model the prediction was made
  with, and carrying it across silently imports the other design's model
  error.
- Rounding the cycle count up unconditionally. A gap ratio that is an
  exact power of the factor is an exact whole count, and rounding it up
  adds a funded foundry run to every such plan.
- Reporting only the counts. Without the residual gap, a plan whose
  inputs disagree with each other looks compliant on the cycle number
  alone.

## Behavior contract (gate 3)

The convergence-factor mapping, the novelty floor, the closure-count
rounding at an exact power of the factor, the residual-gap computation,
the schedule-capacity floor and the freeze verdict are exercised by the
gate 3 contract test: scripts/test_q6012_design_iteration_count.py
against scripts/q6012_design_iteration_count_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_design_iteration_count.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
