---
name: e2021-unwanted-firing-failure-tolerance
description: "Verify that no single failure can make an actuator fire uncommanded, against ECSS-E-ST-20-21C clause 5.1.2. Use when the task is proving single-failure tolerance of an arm, select and fire chain: reading the inhibit inventory with the shared resources each inhibit depends on, collapsing inhibits behind a common bus, driver or command path into one effective independent inhibit, scanning every candidate single failure and every shared resource for one that leaves no inhibit standing, and grading the worst stray current a single failure can drive into the initiator against the no-fire current in decibels. Trigger: ecss, e-st-20-21-actuator-interface, actuator-unwanted-firing-tolerance, arm-select-fire-inhibit-chain, shared-resource-common-cause-collapse, uncommanded-actuation-single-point, stray-current-no-fire-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-21-actuator-interface, e2021-unwanted-firing-failure-tolerance, actuator-unwanted-firing-tolerance, arm-select-fire-inhibit-chain, shared-resource-common-cause-collapse, uncommanded-actuation-single-point, stray-current-no-fire-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuator Interfaces — Unwanted-Firing Failure Tolerance (space-systems/ecss/e2021-unwanted-firing-failure-tolerance)

Use when the task is the reliability requirement of ECSS-E-ST-20-21C
clause 5.1.2 -- showing that the actuation chain of a hold-down,
release or deployment device cannot be driven to fire by one failure
anywhere in it.

## Domain quick reference

- The requirement is about the wrong direction of failure. Most of an
  actuator specification is about firing when commanded; this clause is
  about not firing when not commanded, and the architecture that
  satisfies one can be indifferent to the other.
- Firing is nested behind arm, select and fire events, and each of
  those owes an inhibit. A chain missing one of the three has two
  barriers no matter how good the remaining hardware is, and the gap is
  usually the select stage on a single-device design.
- Counting inhibits is not counting barriers. Two inhibits fed from the
  same secondary bus, driven by the same gate driver or commanded down
  the same serial path are one inhibit against a failure of that shared
  resource. The honest number is the count after collapsing the
  inhibits that share anything.
- Sharing is transitive. Inhibit A and B share a bus, B and C share a
  driver: a single failure cannot take all three, but the collapse
  still merges them into one group, and it is that grouping, not a
  pairwise look, that yields the real count.
- Single-failure tolerance is a set question with a small answer space.
  Every shared resource is itself a candidate single failure, on top of
  the declared failure modes, and each one either leaves an inhibit
  standing or does not.
- A firing path does not need a defeated inhibit if it can put enough
  current into the initiator anyway. The stray current a single failure
  can drive is graded against the no-fire current as a margin in
  decibels, because that is the form the electromagnetic compatibility
  evidence already comes in.

## Workflow

1. Normalise the inhibit inventory: unique identifiers, a barrier from
   the arm, select and fire set, and the named resources each inhibit
   depends on.
2. Report which barriers carry no inhibit at all, before any counting,
   because a missing barrier is a design gap rather than a tolerance
   shortfall.
3. Build the resource map, then merge inhibits sharing any resource,
   transitively, into independence groups; the group count is the
   effective inhibit count.
4. Require at least two effective inhibits, and say plainly in the
   finding how many survived the collapse.
5. Scan the candidate single failures: every shared resource on its
   own, plus every declared failure mode, expanded through the
   resources it takes out as well as the inhibits it names directly.
6. Report each candidate that leaves no inhibit standing by name and
   kind, rather than stopping at the first one found.
7. Convert the worst-case induced current into a margin against the
   no-fire current and grade it, absorbing representation error at the
   boundary with a named tolerance instead of relaxing the requirement.

## Pitfalls

- Counting inhibits off the schematic. Three relay contacts in series
  are three inhibits only if their coils are not driven from one
  supply; the collapse is the whole point of the check and it cannot be
  done by looking at the power path alone.
- Treating a common resource as a common-cause item to be handled in
  the reliability analysis instead of here. A bus every inhibit hangs
  off is a single failure that fires the actuator, which is a
  requirement violation, not a probability to be multiplied down.
- Doing the sharing analysis pairwise. Two inhibits that share nothing
  directly can still be in one group through a third, and a pairwise
  check reports independence that the chain does not have.
- Accepting a declared failure list as the candidate set. The resources
  are candidates in their own right; a list written by the designer
  reflects the failures the designer thought of.
- Proving inhibit independence and stopping. If a single failure can
  inject a stray current above the no-fire level, the initiator fires
  with every inhibit still nominally intact.
- Relaxing the required margin to pass an exactly-met case. Equality at
  the limit is a representation question, handled by the tolerance
  inside the comparison; the required margin stays as specified.

## Behavior contract (gate 3)

The inhibit-inventory validation, barrier coverage, resource mapping,
transitive independence collapse, single-failure scan over resources
and declared failures, and the stray-current no-fire margin are
exercised by the gate 3 contract test:
scripts/test_e2021_unwanted_firing_failure_tolerance.py against
scripts/e2021_unwanted_firing_failure_tolerance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_unwanted_firing_failure_tolerance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
