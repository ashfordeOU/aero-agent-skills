---
name: e2020-additional-switch-placement
description: "Determine where an additional commandable switch belongs along a power line. Use when an ECSS-E-ST-20-20C clause 5.2.13.4.1 layout has to put the extra switch on the power system side of the main switch: walk the ordered source-to-load node list, keep the mountable nodes upstream of the main switch, measure the live harness stub each candidate would leave between the power system output and itself, measure the length it de-energises, drop any candidate above the stub limit or inside the minimum separation from the main switch, and take the feasible node with the shortest stub. Refuses an unordered node list, a first node away from the source and an unknown node id. Trigger: ecss, e-st-20-20c, additional-switch-placement, power-system-side-placement, energised-harness-stub, de-energised-line-length, switch-separation-distance, switch-mounting-node."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-additional-switch-placement, power-system-side-placement, energised-harness-stub, de-energised-line-length, switch-separation-distance, switch-mounting-node, power-line-node-walk]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Additional Switch Placement (space-systems/ecss/e2020-additional-switch-placement)

Use when the task is the placement recommendation of ECSS-E-ST-20-20C
clause 5.2.13.4.1 — deciding where along a power line the additional
commandable switch should sit, with the power system side of the line as
the recommended location, and showing which node on the actual harness
run best satisfies that recommendation.

## Domain quick reference

- A switch de-energises only what is downstream of it. Whatever harness
  runs from the power system output up to the switch stays live whenever
  the bus is live, and no commandable device on this line can clear a
  short inside it. That run is the ENERGISED STUB, and it is the single
  quantity the placement recommendation is really about.
- Putting the extra switch on the power system side means putting it
  between the power system and the main switch, as near the source end
  as the layout allows. The nearer it sits to the output, the shorter
  the stub and the more of the line a command can actually kill.
- The bound in the other direction is physical proximity. Mounted hard
  against the main switch, the two devices share one bracket, one
  connector shell and one local thermal and mechanical environment, so a
  single localised event takes both and the line is back to one point of
  failure. A minimum separation along the run keeps them apart.
- Not every position on a drawing is a location. A splice or a bend in
  the middle of a harness run has a distance from the source but cannot
  carry a switch, its bracket or its command harness; only nodes that
  are genuinely mountable are candidates.
- A node past the main switch is not a placement at all. It can only
  de-energise what the main switch already commands and it leaves the
  entire upstream run live, which is the situation the provision exists
  to remove.
- The line is best described as an ordered node list from the power
  system end to the load end with each node's distance from the source.
  The stub of a placement is then simply that node's distance, and the
  length it de-energises is the remainder of the run.
- The stub limit, the minimum separation and whether the power-system
  side rule is enforced at all are declared project policy rather than
  physical constants; the defaults in the logic module are a starting
  point a project substitutes its own values into.

## Workflow

1. Validate the line topology: at least a source and a load node, the
   first node at the power system output, distances strictly ascending
   from the source, unique node ids and an explicit mounting flag on
   each. A node list that is merely in the right order on the page but
   not in distance is refused.
2. Validate the placement policy: the stub limit, the minimum separation
   from the main switch, and whether the power-system-side rule is being
   enforced on this line.
3. Locate the main switch node on the run; an id the line does not carry
   is refused rather than defaulted.
4. For every other node, measure the stub it would leave, the length it
   would de-energise and its separation from the main switch, and
   establish whether it lies upstream of the main switch and whether it
   can physically carry a switch.
5. Reject a candidate on any of the four questions and say which:
   wrong side, not mountable, stub above the limit, separation below the
   minimum. A node can fail more than one, and all its reasons are
   reported together.
6. Take the acceptable node with the shortest stub, breaking a tie
   towards the larger separation and then by node id so the
   recommendation is deterministic.
7. Report the stub and separation slack of the chosen node, raise an
   advisory when the chosen node de-energises the whole run, and raise
   one when it is the only acceptable node on the line — a layout with
   no fallback position is a schedule risk as soon as that node moves.

## Pitfalls

- Placing the extra switch near the load because that is where the
  bracket was free. It leaves the whole upstream run live, so the
  provision protects the load and not the line, and the harness that a
  command most needs to be able to kill is exactly the part left out.
- Treating any point on the harness as a placement. A splice has a
  distance from the source and no way to hold a switch; a candidate list
  built from drawing positions rather than mounting locations produces a
  recommendation nobody can build.
- Mounting the extra switch immediately beside the main one. The
  arrangement is electrically correct and physically fragile: one burnt
  connector or one local overheat has both devices inside it, which is
  the single point the second switch was added to remove.
- Reporting only the length the switch de-energises. It is the flattering
  half of the same number; the stub is what a reviewer needs, because it
  is the part of the line no command can reach.
- Assuming the node list is ordered because it was written in order. The
  ordering that matters is distance from the power system output, and a
  list that is ordered on the page but not in distance silently inverts
  upstream and downstream.
- Comparing a stub or a separation by bare arithmetic. Both are
  differences of declared distances, so a candidate meant to sit exactly
  on the stub limit or exactly on the minimum separation can land a few
  units in the last place the wrong side of the bound; the comparison
  absorbs that representation error while the limits stay as specified.

## Behavior contract (gate 3)

The node validation, topology ordering, policy validation, node lookup,
line length, energised stub, de-energised length, separation,
power-system-side test, per-node assessment and the full placement
recommendation are exercised by the gate 3 contract test:
scripts/test_e2020_additional_switch_placement.py against
scripts/e2020_additional_switch_placement_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_additional_switch_placement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
