---
name: e3311-distribution-boxes-explosive-delays
description: "Evaluate a detonation distribution box and the explosive delay elements around it against ECSS-E-ST-33-11C clauses 4.11.9 and 4.11.10. Use when the task is splitting one detonation input across several branches and holding a timed sequence: apportioning transferred energy per branch, grading each branch against its initiation threshold with a declared transfer margin, bounding the branch-to-branch simultaneity spread, widening each delay by unit tolerance and temperature drift, and confirming the worst-case corners still keep the events ordered and separated. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, detonation-distribution-box, explosive-delay-element, detonation-transfer-margin, branch-simultaneity-spread, delay-window-temperature-drift, delay-train-event-ordering."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-distribution-boxes-explosive-delays, detonation-distribution-box, explosive-delay-element, detonation-transfer-margin, branch-simultaneity-spread, delay-window-temperature-drift, delay-train-event-ordering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Distribution Boxes and Explosive Delays (space-systems/ecss/e3311-distribution-boxes-explosive-delays)

Use when the task is the detonation distribution box and delay element
specification of ECSS-E-ST-33-11C clauses 4.11.9 and 4.11.10 -- showing
that one detonation input reaches every branch with enough energy to
initiate it, that the branches go off close enough together to count as
simultaneous, and that any deliberate delay still lands inside its
window once tolerance and temperature have been stacked on it.

## Domain quick reference

- A distribution box is an energy divider with no gain. Whatever the
  input donor charge delivers is split across the outputs and reduced
  again by the transfer interface, so the branch that matters is the
  weakest one, not the average one.
- Branch energy is graded against the acceptor initiation threshold as
  a ratio, not a difference. A transfer margin of two on energy is the
  usual floor because a detonation transfer across a gap is sensitive
  to alignment, gap growth and donor lot variation, none of which are
  captured by a single nominal number.
- The transfer medium sets the loss that has to be carried before the
  split: a through-bulkhead initiator crosses a sealed wall and loses
  more than a continuous detonating cord run, and an explosive transfer
  line sits between the two. The loss is a property of the interface,
  so it is declared per branch rather than assumed common.
- Simultaneity is a spread, not a mean. The number that matters is the
  difference between the earliest and the latest branch function time,
  because a separation joint that unlatches at one corner before
  another has already seen an asymmetric load.
- A delay element is a burning column, so its output time moves with
  unit-to-unit tolerance and with temperature. The two widen the window
  in the same direction and both have to be stacked before the window
  is compared with the event it has to hit.
- Ordering is a worst-case question. Two delays whose nominal times are
  comfortably apart can overlap at the corners once both windows are
  opened, and the check is the earliest possible later event against
  the latest possible earlier event, with a declared separation kept
  between them.

## Workflow

1. Declare the input energy the donor delivers, the branch count and
   the transfer medium and acceptor threshold of each branch. Reject a
   branch count that is not a positive whole number and a medium that
   is not one of the declared interfaces.
2. Apportion the input across the branches, applying the per-branch
   transfer loss of its medium, and record the delivered energy each
   acceptor actually sees.
3. Grade every branch as a ratio of delivered energy to its initiation
   threshold against the policy transfer margin, and name the branch
   with the smallest ratio as the one that sizes the box.
4. Take the measured or predicted branch function times, reduce them to
   a spread, and compare that spread with the simultaneity allowance.
5. Open each delay element window: widen the nominal delay by the unit
   tolerance and by the temperature drift the qualification excursion
   produces, and reject a window whose early edge has collapsed to zero
   or below.
6. Walk the delay train in nominal order and confirm each event still
   starts after the previous one finishes, with the declared separation
   left between the windows. Report every overlap as a finding rather
   than only the first one.

## Pitfalls

- Dividing the input energy and stopping there. The split is the easy
  half; the transfer loss at each interface happens after the split and
  is what usually takes a marginal branch below its threshold.
- Grading the transfer on the nominal branch. The box is sized by its
  weakest branch, and a design that passes on the mean fails on the one
  output with the longest run or the sealed bulkhead crossing.
- Reading simultaneity as an average function time. Averaging hides
  exactly the asymmetry the requirement exists to bound, because a
  spread of a millisecond and a spread of a microsecond can share a
  mean.
- Stacking the delay tolerance but not the temperature drift. A delay
  column qualified at room temperature drifts with the flight
  temperature, and the drift is a fraction of the nominal delay, so it
  grows with the longest delays in the train.
- Checking event ordering on nominal times. The ordering that has to
  hold is between window edges, and a pair that is well ordered
  nominally can cross once both windows are opened at the corners.
- Comparing a stacked window edge with a separation limit by bare
  arithmetic. The edges are sums of products, so a case that sits
  exactly on the limit can land a few units in the last place the wrong
  side of it; the comparison absorbs that while the limit is untouched.

## Behavior contract (gate 3)

The branch apportionment, transfer-margin grading, simultaneity spread,
delay-window stacking and train-ordering verdict are exercised by the
gate 3 contract test:
scripts/test_e3311_distribution_boxes_explosive_delays.py against
scripts/e3311_distribution_boxes_explosive_delays_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_distribution_boxes_explosive_delays.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
