---
name: q60-class-1-programmable-logic-devices
description: "Use when a class 1 board carries an FPGA or CPLD. Determine the development, reuse and maintenance route a programmable logic device design takes in class 1 equipment under ECSS-Q-ST-60C clause 4.6.4: group the configuration technology as antifuse one-time, flash-reprogrammable or volatile, compare a reuse candidate against its baseline on device, logic and implementation axes, score the design-assurance record against what the declared origin demands, test the achieved functional coverage against the class 1 floor, then route the design to full development, delta verification or a reviewed reuse and attach the programming and in-service duties the technology carries. Trigger: ecss, q-st-60c-clause-4-6-4, class-1-pld-development-routing, pld-configuration-technology-groups, pld-reuse-delta-axes, pld-design-assurance-coverage, pld-programming-facility-controls, pld-in-service-maintenance-duties."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-1-programmable-logic-devices, class-1-pld-development-routing, pld-configuration-technology-groups, pld-reuse-delta-axes, pld-design-assurance-coverage, pld-programming-facility-controls, pld-in-service-maintenance-duties]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Programmable Logic Devices (space-systems/ecss/q60-class-1-programmable-logic-devices)

Use when the task is clause 4.6.4 of ECSS-Q-ST-60C: a class 1 board carries a
programmable logic device, and the question is not whether the component was
bought correctly but how the design inside it was developed, what a reuse claim
has to carry, and what keeps that design correct after the unit has shipped.

## Domain quick reference

- A programmable logic device is two things at once. It is a component,
  procured against a detail specification like any other part on the list,
  and it is a design the project authored and loaded into that component.
  The general procurement rules cover the first half and say nothing about
  the second, which is the half clause 4.6.4 governs.
- The configuration technology decides the maintenance regime and nothing
  else. An antifuse one-time device is programmed once at a facility and is
  maintained thereafter by replacement. A flash-reprogrammable device holds
  its configuration without power but can be reloaded, so the archive and
  the reload procedure become controlled items. A volatile device reloads
  its configuration at every power-up and can be upset in orbit, so
  scrubbing and an upset-rate assessment are duties, not options.
- Reuse is a claim about axes, not a single fact. A device axis changes the
  silicon the design runs on; a logic axis changes what the design does; an
  implementation axis changes only how the same logic was mapped into the
  same device. Sorting the differences into those three groups is what turns
  a difference list into a route.
- A remap is not a no-op. The same source through a different synthesis tool
  version, a different constraint set or a different pin-out produces a
  different placement with different timing, which is why an
  implementation-only change still owes a delta verification.
- Evidence comes before delta. A design-assurance record short of its
  requirements specification, simulation record, timing analysis or
  post-programming verification is not a small change or a large one; it is
  a claim with nothing behind it, and there is nothing yet to route.
- Coverage is a floor, not a target. The campaign either reached the class 1
  functional coverage floor or it owes the difference, and the shortfall is
  reported in points so the remaining work is a number rather than an
  opinion.

## Workflow

1. Validate the case: the configuration technology, the declared design
   origin, the design-assurance evidence, and for any reuse claim both the
   baseline and the candidate build records. A blank or absent axis is an
   input error, because an axis that cannot be compared cannot be routed.
2. For a declared new design there is no baseline to weigh; route straight
   into the full development flow once the evidence is in hand.
3. Otherwise compare the two build records axis by axis, group the moved
   axes into device, logic and implementation, and take the share of the
   axis set that moved as a reported delta index.
4. Score the design-assurance record against what the declared origin
   demands. If any required item is absent, return that finding and route
   nothing.
5. Compare the achieved functional coverage with the class 1 floor and
   report the shortfall in points, absorbing representation error at the
   floor itself.
6. Route in precedence order: evidence incomplete, then a device or logic
   change to full development, then an implementation change, a coverage
   shortfall or a lapsed baseline record to delta verification, otherwise a
   reviewed reuse. Return the route, the activities it carries, the moved
   axes by group and every finding.
7. Attach the programming and in-service maintenance duties the
   configuration technology carries, and reject a declared post-delivery
   reload of a one-time device outright.

## Pitfalls

- Treating the device procurement as the whole of the obligation. A part
  bought correctly against its detail specification says nothing about the
  design that was loaded into it, and clause 4.6.4 is about the design.
- Calling a rebuild reuse because the source did not change. A new
  synthesis tool version or a new constraint set produces a different
  placement and a different timing closure from identical sources; the
  netlist is the part that did not move and it is not the part the timing
  evidence was taken from.
- Promising a post-delivery reload of an antifuse one-time device. The
  configuration is written once; maintenance of that design is by device
  replacement, and a maintenance plan that assumes otherwise fails the
  first time it is needed.
- Leaving a volatile device without a scrubbing provision because the
  ground test never saw an upset. The configuration memory is exposed for
  the whole mission, and a ground campaign is not the environment the
  provision exists for.
- Routing before the design-assurance record is complete. A reuse route
  granted against a simulation record nobody can produce is a decision with
  no evidence behind it, and it surfaces at the review that needed the
  evidence.
- Comparing the achieved coverage with the floor by bare arithmetic. The
  coverage figure is a ratio of counts turned into a percentage, so a
  campaign exactly on the floor can land a few units in the last place
  below it; the comparison absorbs that representation error while the
  floor stays untouched.

## Behavior contract (gate 3)

The policy merge, build-record validation, axis comparison and grouping,
delta index, design-assurance gap check, coverage floor test, route
precedence, activity-set lookup and technology maintenance duties are
exercised by the gate 3 contract test:
scripts/test_q60_class_1_programmable_logic_devices.py against
scripts/q60_class_1_programmable_logic_devices_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_programmable_logic_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
