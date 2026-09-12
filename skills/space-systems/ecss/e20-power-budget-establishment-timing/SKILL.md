---
name: e20-power-budget-establishment-timing
description: "Use when derive the spacecraft electrical power budget and its margin policy under ECSS-E-ST-20C clause 5.2.1: fix the budget at the phase-B milestone, allocate a maturity-dependent margin to every equipment line (flight-proven, modified, newly developed), roll the lines up into a subsystem demand figure, compare the achieved system-level margin against the margin required at the current project phase, and confirm the budget was re-reviewed at each later phase gate rather than frozen after phase B. Flags a late establishment phase, a skipped phase review, an uncategorized equipment maturity, and a margin erosion below the phase requirement. Trigger: ecss, e-st-20-electrical-scope, power-budget-establishment, phase-b-milestone, power-margin-policy, equipment-maturity-margin, budget-phase-review, power-margin-erosion."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-budget-establishment-timing, power-budget-establishment, phase-b-milestone, power-margin-policy, equipment-maturity-margin, budget-phase-review]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Power Budget Establishment and Phase Review (space-systems/ecss/e20-power-budget-establishment-timing)

Use when the task is the timing and upkeep of the spacecraft power
budget under ECSS-E-ST-20C clause 5.2.1 -- fixing the budget and its
margin policy at phase B, and proving it was reviewed again at each
later project phase instead of being frozen at the phase-B figure.

## Domain quick reference

- Clause 5.2.1 anchors two separate obligations that are easy to
  conflate. The first is an establishment obligation: a power budget
  with an explicit margin policy exists by the end of phase B, when
  the architecture is settled but most equipment is still a prediction
  rather than a measurement. The second is a maintenance obligation:
  that budget is re-opened and re-reviewed at every later phase gate
  (C, D, E), because the inputs that justified the phase-B margin are
  progressively replaced by test data.
- Margin lives at two levels and the two must not be summed twice.
  Equipment-level margin is carried per line and is a function of that
  line's design maturity -- a flight-proven unit reused unchanged
  carries the smallest margin, a modified existing design carries more,
  and a newly developed unit carries the most. System-level margin is
  what remains between the rolled-up budgeted demand and the power the
  source can supply; it is the figure a phase gate actually grades.
- The system-level requirement is allowed to shrink over the project,
  and only in one direction. A large margin is required at phase B
  because the demand figure is soft; by phase D the demand is largely
  measured and a much smaller reserve is defensible. The default
  ladder used here is 20% at phase B, 10% at C, 5% at D and 2% at E.
  A project may substitute its own ladder, but it must be monotonic
  and it must be fixed as part of the margin policy, not renegotiated
  when a gate is about to fail.
- A phase before establishment has no system-margin requirement at
  all. Asking for one is a modelling error, not a pass: there is no
  budget to grade yet, and the correct finding is that the budget is
  not established.

## Workflow

1. Collect every electrical consumer as a budget line: an identifier,
   a predicted consumption, and a design maturity category
   (flight-proven, modified existing, new development). Reject an
   uncategorized maturity before it enters the budget -- an unmargined
   line silently understates demand.
2. Price each line: margin power = predicted power x the maturity
   margin fraction; budgeted power = predicted + margin.
3. Roll the lines up into the subsystem budget (totals for predicted,
   margin and budgeted power). Reject a duplicated equipment
   identifier, which double-counts a consumer.
4. Record the phase at which the budget was first established. Later
   than phase B is a finding; earlier is acceptable and is not.
5. Compute the achieved system margin against the available power:
   (available - budgeted) / available. Compare it against the margin
   required at the current phase; a shortfall is a finding, and a
   negative achieved margin means the budgeted demand already exceeds
   supply.
6. List the phase gates that have passed since establishment and
   confirm a budget review was held at each one. Every gate without a
   review is its own finding.
7. Aggregate the establishment, review-cadence and margin findings;
   the budget is not clause-5.2.1 compliant until all three lists are
   empty.

## Pitfalls

- Treating the phase-B budget as a deliverable that is signed off and
  closed -- clause 5.2.1 makes it a living figure, and a budget with a
  correct phase-B establishment but no phase-C or phase-D review is
  non-compliant even when its numbers still look healthy.
- Applying one flat margin to every equipment line -- a uniform 20%
  over-reserves the flight-proven units and under-reserves the new
  developments, and it hides which lines are actually driving the
  uncertainty when the margin later has to be defended.
- Summing equipment margin and system margin as if they were one
  reserve, or re-applying the system percentage on top of already
  margined lines -- the system figure is the gap to available power,
  computed from the budgeted total, not another additive allowance.
- Loosening the phase ladder when a gate is about to fail. The margin
  requirement tightening from phase B to phase E is the whole point of
  the review cadence; relaxing phase D back to the phase-B value
  converts a real finding into a paper pass.
- Grading a margin at a phase that precedes establishment and reading
  the absent requirement as compliance -- no budget exists there, and
  the finding is the missing budget itself.

## Behavior contract (gate 3)

The maturity-margin pricing, budget roll-up, phase-margin requirement,
establishment-timing and review-cadence logic is exercised by the gate
3 contract test: scripts/test_e20_power_budget_establishment_timing.py
against scripts/e20_power_budget_establishment_timing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_power_budget_establishment_timing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
