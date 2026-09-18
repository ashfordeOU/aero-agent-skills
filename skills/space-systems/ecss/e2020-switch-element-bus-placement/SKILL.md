---
name: e2020-switch-element-bus-placement
description: "Verify that the switching element of a power distribution protection device sits on the energised main bus side. Use when an LCL, HLCL or latching relay branch is reviewed against ECSS-E-ST-20-20C clause 5.2.3.2.1: order the branch from main bus along the energised rail through the load and back to the bus return, confirm the pass element precedes everything it protects, list what stays tied to the bus once it opens, name any reachable connector or harness left live, size the energised stub against its limit, and flag a redundant feed injecting past the element. Trigger: ecss, e-st-20-20c-clause-5-2-3-2-1, lcl-switching-element-placement, energised-main-bus-side-switch, power-branch-isolation-coverage, live-harness-stub-upstream-of-switch, return-side-switch-defect, latching-current-limiter-topology."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-switch-element-bus-placement, lcl-switching-element-placement, energised-main-bus-side-switch, power-branch-isolation-coverage, live-harness-stub-upstream-of-switch, return-side-switch-defect, latching-current-limiter-topology]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Switching Element on the Bus Side (space-systems/ecss/e2020-switch-element-bus-placement)

Use when the task is clause 5.2.3.2.1 of ECSS-E-ST-20-20C -- deciding
which end of a distribution branch the series pass element of a
protection device belongs to. A latching current limiter, a heater
latching current limiter, a fold-back limiter and a latching relay all
contain one element that opens the branch, and the clause fixes where
that element sits: on the side facing the energised main bus, ahead of
everything the device exists to protect.

## Domain quick reference

- The branch is an ordered loop, not a box. It runs from the main bus
  along the energised rail, through whatever the device places in
  series, out through the connector and the harness to the load, and
  back along the return rail to the bus return. The load is the single
  point where the two rails meet, and the position of the switching
  element in that order is the whole of the question.
- Placed on the energised side, the open element leaves the harness,
  the connector and the load at return potential. Nothing downstream
  can be reached from the bus, so an off command means the branch is
  off, and the coverage figure is the share of protected elements the
  open element actually separates.
- Placed on the return side, the open element changes almost nothing.
  The load and the whole feed harness stay tied to the energised bus,
  the load case can float up towards bus potential, and a downstream
  short to structure returns through the structure rather than through
  the open element, so the fault is neither cleared nor seen.
- Two secondary defects hide behind a nominally correct placement. An
  energised stub -- harness upstream of the pass element -- stays live
  whatever the device does, so it is sized against a declared limit
  rather than assumed short. And a redundant or cross-strapped feed
  that lands downstream of the element keeps the branch energised
  while the device reports itself off; the element cannot open a feed
  it is not in series with.
- Reachable interfaces are graded separately from coverage. A
  connector or harness run left live is a handling and a fault
  exposure even when the coverage arithmetic looks acceptable,
  because a percentage says nothing about which element it lost.

## Workflow

1. Write the branch out as an ordered chain and validate it: one main
   bus at the head, one bus return at the tail, one load as the single
   crossing element, energised rail before the load and return rail
   after it. Refuse a chain that cannot be read in that order rather
   than judging a topology nobody described.
2. Locate the switching element in the chain and read the rail it sits
   on. A return-rail element fails the clause outright; so does an
   element that follows the load in the order.
3. Split the chain at the element into what stays live and what the
   open element separates, and compute the coverage fraction over the
   protected set -- the branch minus the two bus ends and the element
   itself.
4. Name every reachable connector and harness run in the live set
   rather than reporting only the fraction.
5. Sum the energised harness upstream of the element and compare that
   stub against the declared limit, absorbing representation error in
   the comparison without relaxing the limit.
6. Check every additional feed against the element position and flag
   any that injects downstream of it.
7. Close with a verdict that stays open while any finding stands.

## Pitfalls

- Reading "the device switches the branch" off a block diagram and
  never asking which rail the pass element is on. Both topologies draw
  identically at block level and behave completely differently once
  the element opens.
- Putting the pass element on the return rail because the drive
  electronics are simpler there. The saving is real and the isolation
  is gone: the load stays at bus potential with the device off.
- Accepting a coverage number without the element names. Losing one
  connector out of six reads as high coverage and is still a live
  connector on a harness a technician will handle.
- Treating a short energised stub as no stub. Harness ahead of the
  element is energised whenever the bus is, so it belongs in a
  declared budget with a limit, not in an assumption.
- Forgetting the cross-strapped feed. A redundant bus landing
  downstream of the element makes the whole placement argument void,
  and nothing in the device's own telemetry will say so.
- Comparing a summed stub length against a limit by bare arithmetic.
  Lengths entered in millimetres and summed into metres land a few
  units in the last place either side of the limit, so the comparison
  absorbs that error while the limit itself is never relaxed.

## Behavior contract (gate 3)

The chain validation, rail and order checks, live and isolated split,
isolation coverage fraction, reachable interface list, energised stub
budget and downstream feed detection are exercised by the gate 3
contract test: scripts/test_e2020_switch_element_bus_placement.py
against scripts/e2020_switch_element_bus_placement_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_switch_element_bus_placement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
