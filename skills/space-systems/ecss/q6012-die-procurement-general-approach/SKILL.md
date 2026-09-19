---
name: q6012-die-procurement-general-approach
description: "Size a microwave die procurement end to end, from wafer start to accepted delivery, under the general approach of ECSS-Q-ST-60-12C clause 10.1. Use when a buyer must decide how many wafers to start so a flight quantity still exists at the far end of the route: validate the declared stage chain against the canonical order, refuse a repeated or unknown stage, multiply the per-stage yields into a cumulative survival fraction, work the required quantity plus its contingency back to a wafer start, step that start up until the floored forward projection actually meets it, and name every stage with no owner or no exit criterion. Trigger: ecss, q-st-60-12c-clause-10-1, die-procurement-general-approach, microwave-wafer-start-sizing, die-route-cumulative-yield, die-route-stage-ownership, die-delivery-quantity-projection."
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
  tags: [ecss, q-st-60-microwave-die-scope, q6012-die-procurement-general-approach, microwave-wafer-start-sizing, die-route-cumulative-yield, die-route-stage-ownership, die-delivery-quantity-projection, die-route-sequence-integrity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Procurement General Approach (space-systems/ecss/q6012-die-procurement-general-approach)

Use when the task is the framing step of ECSS-Q-ST-60-12C clause 10.1
— placing the whole journey of a microwave die, from the wafer that
has not been started yet to a delivery the customer has accepted, and
answering the question that framing exists to answer: how many wafers
have to enter the route for the flight quantity to leave it.

## Domain quick reference

- The route is a fixed chain: wafer fabrication, wafer acceptance,
  dicing, die visual inspection, die screening, die lot acceptance,
  packing and storage, delivery acceptance. Each link removes part of
  the population, and none of them puts anything back.
- The population changes unit halfway. Everything up to dicing is
  counted in wafers; everything after it is counted in dies. Dicing is
  the transition, and a sizing that never changes unit silently
  multiplies a wafer count by a die yield.
- The cumulative survival fraction is the product of the per-stage
  yields. Working a required delivery quantity back through it gives
  the analytic wafer start, which is a lower bound and not the answer.
- Part counts are floored, not rounded, at every stage: half a wafer
  does not go into the diesaw and nine tenths of a die is not shipped.
  Flooring accumulates against the buyer, so the analytic start is
  stepped up one wafer at a time until the forward projection really
  meets the target, and the number of steps is reported rather than
  hidden inside a fudged yield.
- Contingency belongs on the target, not on the yields. Padding a
  yield to cover attrition corrupts the survival figure every later
  calculation reuses; enlarging the delivery target leaves the process
  data honest and keeps the pad visible.
- A stage with no named owner has no handover, and a stage with no
  exit criterion cannot be closed. Both are route defects independent
  of the arithmetic — the quantities can work perfectly while nobody
  can say who accepts the lot or on what basis.

## Workflow

1. Validate each declared stage against the canonical route: fold the
   spelling, refuse an unknown stage, refuse a stage declared twice,
   and refuse a yield outside the zero-to-one interval.
2. Report the canonical stages the declaration leaves out and the
   pairs declared out of sequence; neither stops the arithmetic, both
   stop the route being called complete.
3. Multiply the yields into the cumulative survival fraction for one
   wafer travelling the whole chain.
4. Enlarge the required delivery quantity by the declared contingency
   to get the target, then divide back through the dies per wafer and
   the survival fraction, rounding up, for the analytic start.
5. Project that start forward stage by stage, flooring at every stage
   and switching the unit at dicing, and compare what leaves the last
   stage with the target.
6. While the projection falls short, raise the start by one wafer, up
   to the named adjustment bound; report the adjustment used, and
   report a case that the bound cannot reach rather than looping.
7. Name the stages without an owner and the stages without an exit
   criterion, and call the case viable only when the quantities work
   and neither list has an entry.

## Pitfalls

- Rounding instead of flooring the surviving population. Rounding up
  invents parts that do not exist and lets a sizing pass on paper that
  arrives one die short of the build.
- Treating the analytic start as the answer. It ignores the flooring
  at every stage, and on a short route with a low yield it can be a
  whole wafer light — the projection is what decides.
- Padding the yields to cover contingency. The survival figure is
  reused by every later sizing; putting the pad there makes each of
  them optimistic by an amount nobody can recover afterwards.
- Multiplying a wafer count by a die yield. Without an explicit unit
  transition at dicing the two populations mix, and the error is large
  enough that it usually looks like a yield problem instead.
- Grading the route on quantities alone. A chain that sizes correctly
  but leaves lot acceptance unowned has no acceptance point, and the
  first real delivery is where that gets discovered.

## Behavior contract (gate 3)

The stage validation, route sequence and coverage findings, cumulative
survival, analytic start, floored forward projection with its unit
transition, the bounded step-up sizing and the ownership and exit
criterion gaps are exercised by the gate 3 contract test:
scripts/test_q6012_die_procurement_general_approach.py against
scripts/q6012_die_procurement_general_approach_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_die_procurement_general_approach.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
