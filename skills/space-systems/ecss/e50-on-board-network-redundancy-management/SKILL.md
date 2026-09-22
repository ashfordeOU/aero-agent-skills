---
name: e50-on-board-network-redundancy-management
description: "Assess whether an on-board network actually survives a failure in the path it is using, under ECSS-E-ST-50C clause 5.7.2.5, where redundancy is managed only when there is somewhere to go and time enough to get there. Compare the nominal and redundant paths element by element to find what both depend on, separating a shared element the design accepted by name from one nobody noticed, then add detection, decision and reconfiguration into an outage and weigh it against what the mission tolerates. Report the detection budget that remains. Use when reviewing on-board network redundancy. Trigger: ecss, e-st-50-communications, on-board-network-redundancy-management, network-path-single-point-of-failure, network-switchover-outage-budget, redundant-path-overlap, failure-detection-time-budget."
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
    clause: 5.7.2.5
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-on-board-network-redundancy-management, on-board-network-redundancy-management, network-path-single-point-of-failure, network-switchover-outage-budget, redundant-path-overlap, failure-detection-time-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Network Redundancy Management (space-systems/ecss/e50-on-board-network-redundancy-management)

Use when a redundant on-board network arrangement is being reviewed, per
ECSS-E-ST-50C clause 5.7.2.5 — whether a failure in the path in use is
survived, and whether it is survived quickly enough to matter.

## Domain quick reference

- Two properties decide it, and they are usually owned by different
  people. Topology says whether there is anywhere to go. Timing says
  whether the move happens soon enough.
- An element carried by both paths is a single point of failure. When
  it fails, both paths fail with it, and no switching logic recovers
  anything. Redundant hardware either side of a shared element buys
  nothing for a failure in the middle.
- Some shared elements are accepted on purpose — a passive backplane, a
  structural harness — but only when the design names them. An
  acceptance that lives in someone's head is indistinguishable from an
  oversight at the next review.
- An acceptance for an element the paths do not actually share is its
  own defect. It usually means a path was renamed and nobody revisited
  what the acceptance covered.
- The outage runs from the failure to traffic flowing again: detecting
  it, deciding to switch, reconfiguring. Sizing on reconfiguration
  alone understates it by the part that is hardest to bound.
- The useful inverse is the detection budget: what is left of the
  tolerated outage once decision and reconfiguration are fixed. When it
  is negative there is no detection fast enough, and the design has to
  change somewhere else.
- Topology outranks timing in the verdict but must not erase it. A
  design with a shared element is usually too slow as well, and fixing
  one leaves the other waiting.

## Workflow

1. List the nominal path and the redundant path as ordered elements.
   Reject a repeated element in a path: it is a naming error, and it
   makes the overlap count wrong.
2. Name the network's own services for managing the redundancy: the
   one that decides which of the underlying buses carries traffic, and
   the one that rewrites addressing and routing so the redundant units
   are reached once it has decided. Those two are the clause's
   examples rather than the whole of what a design may need, so record
   any further service the switch depends on. Two paths with nothing
   to move traffic between them is redundant hardware, not managed
   redundancy.
3. Take the intersection. Those are the elements both paths depend on.
4. Remove the shared elements the design accepted by name, and refuse
   an acceptance for anything the paths do not actually share.
5. Whatever is left is a single point of failure, and it decides the
   first half of the verdict.
6. Add detection, decision and reconfiguration into the switchover
   outage.
7. Compare that outage against the tolerated one with a relative
   tolerance. A budget landing exactly on the bound must pass on every
   platform rather than on the host that rounded kindly.
8. Report the detection budget left, or say plainly that decision and
   reconfiguration alone already overrun it.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.7.2.5a | 2 |

## Pitfalls

- Counting redundant boxes instead of comparing paths. Two of
  everything either side of one shared connector is one path with
  decoration.
- Accepting a shared element in conversation. If it is not in the
  input, the next reviewer sees a single point of failure and the
  argument is had again from scratch.
- Sizing the outage on reconfiguration. Detection is usually the
  largest term and always the least bounded, and leaving it out makes
  the budget look comfortable.
- Treating an overrun as a detection problem without checking. When
  decision and reconfiguration alone exceed the tolerated outage, a
  faster detector changes nothing.
- Deciding the outage with a bare inequality. Two arithmetically
  identical budgets can straddle the bound on different machines, so
  the verdict depends on the build host.
- Stopping at the topology verdict. The shared element is fixed, the
  switchover is still too slow, and that was visible in the same run.

## Behavior contract (gate 3)

Path and duration validation, the shared-element intersection, named
acceptance with refusal of an acceptance for an unshared element, the
three-term switchover outage, the tolerated-outage comparison with a
tolerance at the bound, the detection budget including the case where
none exists, and a topology verdict that outranks timing without
hiding it are exercised by the gate 3 contract test:
scripts/test_e50_on_board_network_redundancy_management.py against
scripts/e50_on_board_network_redundancy_management_logic.py (stdlib
unittest, offline).
Run:
python3 scripts/test_e50_on_board_network_redundancy_management.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
