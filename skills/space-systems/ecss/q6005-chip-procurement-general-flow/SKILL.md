---
name: q6005-chip-procurement-general-flow
description: "Map the overall arrangement for buying bare chips used inside hybrid circuits onto an activity flow under ECSS-Q-ST-60-05C clause 8.1, then grade and schedule it. Use when a programme has to show how dice reach assembly: lay out specification issue, source selection, order placement, wafer lot acceptance, electrical probe, visual inspection, traceability, inert-cover packing, receipt inspection and release, confirm every mandatory activity appears and every prerequisite is genuinely reachable through the declared links, reject a cycle, then compute earliest start and finish in working days, the total duration and the critical path. Trigger: ecss, q-st-60-05-hybrid-microcircuits, bare-die-procurement-flow, wafer-lot-acceptance-sequencing, die-receipt-inspection-ordering, procurement-activity-critical-path, inert-cover-die-storage."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuits, bare-die-procurement-flow, wafer-lot-acceptance-sequencing, die-receipt-inspection-ordering, procurement-activity-critical-path, inert-cover-die-storage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Chip Procurement General Flow (space-systems/ecss/q6005-chip-procurement-general-flow)

Use when the task is the general chip procurement arrangement of
ECSS-Q-ST-60-05C clause 8.1: the activity flow a programme follows to buy the
bare dice that go inside its hybrid circuits, from procurement specification
through to release of those dice to assembly.

## Domain quick reference

- Buying a bare chip is a sequence of activities, not a purchase. A die
  arrives with no package to protect it, no lead frame to test it through and
  no marking to identify it, so everything the package would normally carry
  has to be carried by the flow instead.
- The arrangement runs: issue the procurement specification, select a source
  against it, place the order, accept the wafer lot, probe the dice
  electrically, inspect them visually, record lot traceability, pack and
  store under an inert cover, inspect on receipt, release to hybrid assembly.
- Order is the content of the clause. Probing before wafer lot acceptance
  spends effort on a lot that may not be accepted; visual inspection before
  probing hands the inspector dice that will be scrapped electrically; a
  traceability record written after packing has lost the link between the
  wafer and the carrier.
- A missing link is a different defect from a missing activity, and it is the
  one that hides. Two activities both present but never joined will schedule
  in parallel and read as a valid flow, while in practice nothing enforces
  that the earlier one finished first. Grade reachability, not presence.
- Optional activities exist and are not defects: a supplier line audit, a
  radiation lot verification on the wafer lot, a nonconformance disposition
  after receipt. They attach to the arrangement; they never replace part of it.
- Ownership moves between programmes. The hybrid manufacturer usually writes
  the specification and inspects on receipt, the die supplier usually runs
  lot acceptance, probing and packing, and a procurement agent may place the
  order. A deviation is worth reporting, not rejecting.
- Durations are whole working days and the longest chain is the critical
  path. A long parallel branch that is never joined back does not lengthen
  the delivery, and that is exactly the case worth showing a planner.

## Workflow

1. List the activities the programme proposes, each with a duration in whole
   working days, an owner from the recognised parties, and the activities it
   declares as predecessors.
2. Reject the flow before grading when an activity name is unrecognised, a
   duration is zero, negative or fractional, an owner is not a recognised
   party, an activity precedes itself, a predecessor repeats, an activity is
   duplicated, or a predecessor is not in the flow at all.
3. Order the flow topologically. A set of activities that cannot be ordered
   contains a cycle, and the cycle members are named rather than the flow
   simply being called invalid.
4. Check every mandatory activity of the arrangement is present.
5. For each canonical prerequisite pair whose two activities are both in the
   flow, check the later one is reachable from the earlier through the
   declared links. An unreachable pair is a forgotten link.
6. Compare each activity's owner against the party that normally carries it
   and record deviations separately from the blocking findings.
7. Schedule: every activity starts when its last predecessor finishes. Read
   off the total duration and walk the critical path back from the last
   finish.
8. Report the order, the schedule, the duration, the critical path, the
   findings and whether the arrangement is complete.

## Pitfalls

- Grading presence and calling the flow correct. Ten activities in a list
  with no links between them passes a presence check and schedules as ten
  parallel days of nothing enforced.
- Putting visual inspection ahead of the electrical probe because it is
  cheaper. It is cheaper on dice that are going to be delivered, and wasted
  on dice the probe is about to reject.
- Treating an optional activity as a substitute. A supplier line audit does
  not stand in for wafer lot acceptance, and a radiation lot verification
  does not stand in for the probe.
- Scheduling the inert-cover packing as paperwork. It sits on the critical
  path between traceability and receipt, and a die stored uncovered is a die
  whose surface condition is no longer the one that was inspected.
- Assuming the longest parallel branch drives the delivery. Only a branch
  joined back into the chain does; an unjoined one is a warning about a
  missing link, not a schedule driver.
- Reporting an owner deviation as a failure. Programmes legitimately move
  activities between the customer, the supplier and the manufacturer.

## Behavior contract (gate 3)

The activity validation, flow construction, cycle detection, reachability
grading of prerequisite links, owner comparison, working-day scheduling,
duration and critical-path derivation are exercised by the gate 3 contract
test: scripts/test_q6005_chip_procurement_general_flow.py against
scripts/q6005_chip_procurement_general_flow_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6005_chip_procurement_general_flow.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
