---
name: e2008-sca-qualification-schedule
description: "Validate the production and test schedule of clause 6.4.2 of ECSS-E-ST-20-08C followed when qualifying a cell assembly design: confirm every production, test and documentation step is declared, hold each step behind the steps it depends on rather than merely present somewhere in the list, walk the coupon batch through the declared order to the step that empties it, and rank the findings into one schedule verdict. Use when a qualification flow chart, coupon batch sizing or test sequence plan has to be assessed. Trigger: ecss, e-st-20-08c, sca-qualification-schedule, solar-cell-assembly-qualification-sequence, sca-qualification-step-precedence, sca-qualification-coupon-batch-sizing, sca-baseline-and-final-measurement-order."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-qualification-schedule, e-st-20-08c, sca-qualification-schedule, solar-cell-assembly-qualification-sequence, sca-qualification-step-precedence, sca-qualification-coupon-batch-sizing, sca-baseline-and-final-measurement-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Qualification Schedule (space-systems/ecss/e2008-sca-qualification-schedule)

Use when the task is clause 6.4.2 of ECSS-E-ST-20-08C: the production and
test schedule followed when a cell assembly design is qualified. This
leaf reads a declared sequence of steps and a coupon batch, and returns
the steps that cannot run where they are placed, the steps nobody
declared, and the step at which the batch runs out.

## Domain quick reference

- Order is the content of the schedule, not its presentation. A test
  placed before the production step that made its article measures
  nothing, and an exposure placed before the baseline measurement leaves
  no before-and-after to read the result against.
- Presence and position are separate questions. A step that appears in
  the list but sits ahead of what it depends on is not a covered step,
  and a plan reviewed by ticking names off a list passes that schedule
  every time.
- The baseline brackets the campaign. Visual and electrical
  measurements before the exposures are what the measurements after them
  mean anything against; a final measurement with no initial one is a
  number with nothing to compare it to.
- The batch is consumed as the schedule runs. Environmental exposures
  and the discharge test take coupons out of circulation, so the batch
  has to be sized against the whole sequence and not against the largest
  single step.
- The batch is walked in the declared order, not summed. Two schedules
  with the same total demand fail at different steps, and the step where
  the batch empties is the one the coupon order has to be placed
  against.
- A margin is held above the demand. A batch sized exactly to
  consumption leaves a single anomalous coupon able to stop the
  campaign, so the demand carries a declared margin and the comparison
  is made against that.
- The three arms are ranked, not merged. An absent prerequisite is
  reported ahead of a misplaced one, and a misplaced one ahead of a
  coupon shortfall, because re-sizing a batch for a sequence still in
  the wrong order buys hardware for a schedule nobody can run.
- The report closes the schedule. A documentation step sitting anywhere
  but last describes a campaign that had not finished when it was
  written, which policy can waive but never by accident.

## Workflow

1. Read the declared sequence and the coupon batch it starts with.
   Reject an unknown step, a repeated step or an empty sequence rather
   than grading a list nobody can run.
2. Index the declared positions and resolve each step's prerequisites
   into two separate lists: the ones absent from the sequence entirely
   and the ones placed after the step that needs them.
3. Walk the coupon batch through the declared order, recording the
   opening and closing balance at every step and the step at which it
   empties.
4. Size the starting batch against the total consumption plus the
   declared margin.
5. Rank the arms into one step verdict: absent prerequisite first, then
   misplacement, then coupon shortfall.
6. Roll the schedule up: name the steps nobody declared, group the rest
   by verdict, test that the documentation step closes the sequence,
   report the declared share of the required step set, and return a
   verdict that is clean only when nothing is open.

## Pitfalls

- Grading a schedule by ticking step names off a list. Every
  out-of-order plan passes that review, and the ones that fail are the
  ones that also forgot a step.
- Sizing the coupon batch against the largest single step. Consumption
  accumulates across the sequence, so a batch that covers the worst step
  still empties before the last one.
- Summing the coupon demand instead of walking it. The total says
  whether the batch is big enough; only the walk says which step stops,
  and that is the step the procurement has to be timed against.
- Placing the environmental exposures before the baseline measurements.
  The exposure still runs, the coupons are still spent, and the result
  cannot be read as a change in anything.
- Merging the arms into one pass or fail. A schedule missing a step and
  a schedule holding all of them in the wrong order need different
  corrections, and one verdict asks for the same one twice.
- Waiving the documentation placement silently. Closing the campaign
  with a report written before the last test is a project decision, so
  it is read from policy rather than assumed by whoever drew the chart.

## Behavior contract (gate 3)

The required step set, the prerequisite resolution into absent and late
lists, the coupon walk with its per-step balance, the batch demand with
margin, the ranked step verdict and the rolled-up schedule completeness
and documentation placement are exercised by the gate 3 contract test:
scripts/test_e2008_sca_qualification_schedule.py against
scripts/e2008_sca_qualification_schedule_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_qualification_schedule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
