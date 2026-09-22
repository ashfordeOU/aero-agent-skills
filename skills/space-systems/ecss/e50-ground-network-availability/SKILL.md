---
name: e50-ground-network-availability
description: "Derive the availability budget of a ground network against ECSS-E-ST-50C clause 5.8.6, a single requirement that the network be there for every scheduled operation. Build each element from its mean time between failures and repair time, charge preventive downtime, fold redundant members into a group, compose the chain, and restate the result as the outage seconds the reporting period allows. Rank elements by the share of unavailability each spends, and invert the chain into the per-element availability or repair time a target needs. Use when apportioning an end-to-end availability requirement across ground elements, or grading a proposed chain. Trigger: ecss, e-st-50-ground-network, ground-network-availability-budget, mtbf-mttr-element-availability, series-chain-availability-composition, outage-seconds-per-year-budget, availability-apportionment-inverse."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.8.6
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-ground-network, e50-ground-network-availability, ground-network-availability-budget, mtbf-mttr-element-availability, series-chain-availability-composition, outage-seconds-per-year-budget, availability-apportionment-inverse]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Ground Network Availability (space-systems/ecss/e50-ground-network-availability)

Use when a ground network carries an availability requirement per
ECSS-E-ST-50C clause 5.8.6 — turning a single end-to-end figure into a
budget the elements of the chain can be held to, and turning a proposed
chain back into a verdict against it.

## Domain quick reference

- The clause is one sentence and the work behind it is not. It asks
  that the network be there for every scheduled operation, and
  answering that takes one discipline applied end to end: every element
  has an availability, the chain composes, and the composed number is
  what the mission was promised.
- An element's availability comes from two numbers, not one. How often
  it fails and how long it takes to get back; a mean time between
  failures quoted without a repair time says nothing about service.
- Preventive maintenance is downtime too. Inherent availability charges
  only corrective repair, and a network graded on it will overstate what
  the mission actually gets by exactly the planned outage.
- Series composition multiplies and is unforgiving. A chain is always
  worse than its worst element, and adding a nominally excellent element
  still costs availability.
- Redundancy composes the other way, on the unavailability. One minus
  the product of the members being down, which is why the first spare
  buys an order of magnitude and the second buys much less.
- An availability without a period is not a budget. The same fraction is
  five minutes a year or a second a day, and only one of those is a
  number an operations team can plan against.
- Unavailability adds almost linearly along a chain, so the share each
  element spends is the ranking a review actually needs. The element at
  the top of that list is where the next euro goes.

## Workflow

1. List the chain element by element, each with a name and either a
   stated availability or a failure and repair time pair, and say which
   elements are redundant and how many members they have.
2. Fix the window the requirement bites in: the operations scheduled on
   the spacecraft across the reporting period — every pass, every
   manoeuvre, every commanding window the plan holds — because the
   network is owed to all of them, and a figure averaged over the idle
   time between them hides an outage that lands on one.
3. Build each element's availability, charging preventive downtime where
   the element has planned maintenance. Fold redundant members into a
   group before the element enters the chain.
4. Compose the chain in series. Do not average the elements and do not
   quote the worst one; both understate a long chain differently.
5. Restate both the achieved and the required figure as outage seconds
   over the period the requirement is written for, so the comparison is
   in units an operations team can act on.
6. Grade with a relative tolerance against the requirement, over the
   scheduled operations fixed above rather than over the calendar, and
   grade again against the requirement stiffened by whatever headroom
   factor the project asks for, so a chain that only just passes is
   reported as only just passing.
7. Rank the elements by the share of chain unavailability each spends,
   and name the top one.
8. Where the chain misses, compute the inverse: the per-element
   availability the chain needs, or the repair time one element needs,
   and check that recommendation back through the same composition.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.8.6a | 6 |

## Pitfalls

- Quoting inherent availability as the service figure. It omits planned
  maintenance, and the gap between the two is exactly the outage the
  operations team will be asked to explain.
- Averaging element availabilities. A chain is a product; the average is
  always optimistic and gets worse the longer the chain.
- Dividing an end-to-end target by the element count. Apportionment in a
  series chain is the count-th root, not the quotient.
- Counting a redundant pair as twice one element. Redundancy composes on
  the unavailability, and treating it as a series or an additive term
  gets the sign of the effect wrong.
- Reporting an availability with no period attached. The fraction is not
  actionable; the outage seconds over a stated period are.
- Deciding compliance with a bare inequality at the requirement. A chain
  sized to land exactly on its target is then decided by rounding, and
  two build hosts can disagree.
- Treating a target of exactly one as a repair-time requirement. No
  finite repair time reaches it, and answering with zero reads as an
  achievable number.

## Behavior contract (gate 3)

Availability and element-record validation, inherent versus operational
availability, series and redundant-group composition, the outage-seconds
restatement, the apportionment and repair-time inverses each re-checked
against the same composition, the contribution ranking, and the verdict
bands at the exact requirement and the exact headroom bound are
exercised by the gate 3 contract test:
scripts/test_e50_ground_network_availability.py against
scripts/e50_ground_network_availability_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e50_ground_network_availability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
