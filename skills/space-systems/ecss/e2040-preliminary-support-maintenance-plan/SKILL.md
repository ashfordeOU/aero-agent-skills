---
name: e2040-preliminary-support-maintenance-plan
description: "Plan the post-delivery support ECSS-E-ST-20-40C clause 5.2.5 asks a supplier to think through while the device is still being defined: size the support window in months, report a maintenance task whose interval is so long it never falls due inside it, turn operating hours and mean time between failures into an expected spares demand and compare it with what is actually held, find the parts whose end of life lands inside the support window with no mitigation behind them, size a lifetime buy against the demand it has to cover, and report mitigation coverage against target. Use when a support and maintenance plan is first drafted or reviewed. Trigger: ecss, e-st-20-40-device-scope, preliminary-support-maintenance-plan, post-delivery-support-window, maintenance-interval-feasibility, spares-demand-from-mtbf, part-obsolescence-mitigation, lifetime-buy-sizing."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-preliminary-support-maintenance-plan, post-delivery-support-window, maintenance-interval-feasibility, spares-demand-from-mtbf, part-obsolescence-mitigation, lifetime-buy-sizing, support-plan-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Preliminary Support and Maintenance Plan (space-systems/ecss/e2040-preliminary-support-maintenance-plan)

Use when the task is the early support duty of ECSS-E-ST-20-40C clause
5.2.5 -- planning, while the device is still being defined, how it will
be supported after delivery: what is maintained and how often, what is
held as spares, and which parts will stop being available before the
support obligation ends.

## Domain quick reference

- The support window is the frame every other figure is measured
  against. It is a duration in months, and a plan that never states it
  cannot say whether anything in it is sufficient.
- A maintenance task is defined by its interval, and an interval longer
  than the support window means the task never falls due. It reads as
  diligence in the plan and buys nothing, while the task that should
  have been there is missing.
- Spares are sized from failure rate, not from intuition. Total
  operating hours across the units in service, divided by the mean time
  between failures, is the expected demand, and the holding is compared
  against it rather than against a round number.
- A demand of a fraction of a unit is still a demand. Rounding it away
  is how a plan ends up holding nothing for the part that fails once
  every two missions.
- Obsolescence is a date problem. A part whose end of life falls inside
  the support window needs a mitigation behind it -- a lifetime buy, a
  qualified alternate, or a planned redesign -- and a part at risk with
  none is the finding this plan exists to surface.
- A lifetime buy is only a mitigation if it is sized. The quantity has
  to cover the demand from the end-of-life date to the end of the
  support window, and a buy sized by budget rather than by demand runs
  out before the obligation does.
- Coverage and demand comparisons land exactly on their bounds, so each
  one absorbs the representation error of a division rather than
  failing a plan that is precisely sufficient.

## Workflow

1. Resolve the support window: a positive number of years converted to
   months, the operating hours per year, and the units in service.
   Refuse a non-positive window rather than defaulting it.
2. Resolve the maintenance tasks: unique names, a positive interval,
   and a duration. Report any task whose interval exceeds the window so
   that it never falls due.
3. Count how many times each remaining task falls due inside the
   window, absorbing representation error at an exact division.
4. Resolve the spares: unique part names, a positive mean time between
   failures, and the quantity held. Compute the expected demand from
   the total operating hours and compare it with the holding.
5. Resolve the obsolescence list: unique parts, an end-of-life year and
   a folded mitigation. Report a part whose end of life falls inside
   the support window carrying no mitigation.
6. For a lifetime buy, size the demand from the end-of-life date to the
   end of the window and report a quantity that does not cover it.
7. Compute the share of at-risk parts actually mitigated, compare it
   against the target, and return the findings with the figures.

## Pitfalls

- Writing a maintenance interval longer than the support obligation.
  The task list looks complete, every entry is individually reasonable,
  and nothing in it is ever performed.
- Rounding a fractional spares demand down to zero. The parts that fail
  less than once per support period are exactly the ones with no spare
  on the shelf when they do.
- Treating a lifetime buy as a mitigation without sizing it. The
  mitigation column reads as green, and the quantity was set by what
  was affordable in the year it was bought.
- Measuring obsolescence risk against the delivery date instead of the
  end of the support window. Every part looks available, because the
  question asked was whether it is available now.
- Comparing a spares holding against a computed demand with a strict
  inequality. A holding that exactly equals the demand can sit a unit
  in the last place below it and flag a plan that is precisely
  sufficient.

## Behavior contract (gate 3)

The support window sizing, maintenance interval feasibility and
occurrence count, spares demand from mean time between failures,
obsolescence risk against the window, lifetime-buy sizing and the
coverage comparison are exercised by the gate 3 contract test:
scripts/test_e2040_preliminary_support_maintenance_plan.py against
scripts/e2040_preliminary_support_maintenance_plan_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_preliminary_support_maintenance_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
