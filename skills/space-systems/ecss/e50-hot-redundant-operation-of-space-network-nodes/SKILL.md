---
name: e50-hot-redundant-operation-of-space-network-nodes
description: "Assess whether a nominal and redundant network node pair truly operates hot redundantly on a spacecraft on-board network, per ECSS-E-ST-50C clause 5.7.1.6. Confirm both units are powered and attached rather than cold spares, confirm the standby cannot drive the medium or answer to the active unit's address, check the pair is cross-strapped across segments instead of sharing one, and compare detection, switchover and re-initialisation time against the allowed outage. Use when reviewing a redundancy concept or a failover budget. Trigger: ecss, e-st-50-communications, hot-redundant-network-node, network-node-cross-strapping, standby-output-inhibit, duplicate-node-address-conflict, failover-outage-budget."
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
  tags: [ecss, e-st-50-communications, e50-hot-redundant-operation-of-space-network-nodes, hot-redundant-network-node, network-node-cross-strapping, standby-output-inhibit, duplicate-node-address-conflict, failover-outage-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Hot Redundant Operation of Space Network Nodes (space-systems/ecss/e50-hot-redundant-operation-of-space-network-nodes)

Use when a redundant pair of nodes sits on one on-board network under
ECSS-E-ST-50C clause 5.7.1.6 — deciding whether the pair is genuinely hot
redundant, and whether having both units live is safe for the network.

## Domain quick reference

- Two items sit at this clause and they pull against each other. The
  first asks that both units be powered and attached at once, so a
  takeover costs a switchover rather than a power-up. The second asks
  that having both units there does not itself harm the network, and
  that the takeover is fast enough to be worth having.
- The first item is a state question with no middle ground. A unit that
  is unpowered is a cold spare; a unit powered but off the network is a
  warm spare. Both may be perfectly good designs, but neither is what
  this clause calls hot, and the distinction is what sets the outage.
- A second powered transmitter on a shared medium is a new failure mode,
  not redundancy. Exactly one output may be enabled at a time, and the
  inhibit on the standby is the thing that makes hot redundancy safe
  rather than dangerous.
- A hot standby you cannot poll is a hot standby you cannot trust. If
  both units answer to one address while both are attached, nothing can
  confirm the standby is healthy, and the first proof it was not is the
  failed takeover.
- Cross-strapping is about what one segment failure costs. The pair is
  only exposed when BOTH units hang off the same single segment; as
  soon as one unit has a second path, losing a segment costs a unit and
  not the function.
- The outage is a chain, not a switch. Detecting the fault, commanding
  the switchover and re-initialising the incoming unit all run before
  the function is back, and it is their sum that the system budget
  applies to.

## Workflow

1. State each unit fully: powered, attached, the segments it reaches,
   its address, and whether its transmitter is enabled. Refuse a
   missing field rather than assuming it — an assumed "attached" is
   precisely the ambiguity this clause exists to remove.
2. Settle the first item: both units powered and attached, or not. Where
   not, name which unit and whether the design is a cold or a warm
   spare, because the remedy differs.
3. Collect every way the pair being live at once harms the network: two
   enabled transmitters, and one address answering for both while both
   are attached. Report all of them, not the first.
4. Test the segment exposure: a single point exists only when both
   units are confined to the same one segment.
5. Add detection, switchover and re-initialisation into the failover
   outage, and compare with the budget using a relative tolerance so a
   chain sized to exactly meet it passes everywhere.
6. Where the outage is too long, give the number back: the detection
   time the budget leaves, or the statement that switchover and
   re-initialisation alone spend it and the takeover itself has to
   shorten.
7. Where no outage budget was declared, report the chain and say it was
   not graded. An absent budget is not a satisfied one.

## Pitfalls

- Reading "redundant" off the block diagram. The diagram shows two
  boxes; the clause asks whether the second one is powered, attached
  and inhibited, and those three are configuration, not topology.
- Leaving the standby transmitter enabled because it is "only
  listening". A powered output on a shared medium can corrupt the
  active unit's traffic, which turns a redundancy into a common-cause
  fault.
- Giving both units one address for a clean takeover and stopping
  there. The takeover is clean and the standby is unmonitorable, so its
  failure stays invisible until it is needed.
- Calling a pair cross-strapped because each unit has two connectors.
  What matters is whether any single segment failure takes both, which
  is a question about the segments they reach, not the connectors they
  carry.
- Budgeting the switchover alone. Detection usually dominates, and
  re-initialisation of the incoming unit is often longer than both, so
  a switchover-only figure understates the outage by most of it.
- Grading a failover against no stated budget. Reporting a chain as
  acceptable when nothing said what acceptable was is a verdict
  invented by the tool.
- Deciding the outage comparison with a bare inequality. A chain built
  to exactly meet its budget then passes on one host and fails on
  another.

## Behavior contract (gate 3)

Unit validation including missing and mistyped fields, the powered and
attached test for the first item, both network conflicts reported
together, the single-segment exposure and the three ways it is avoided,
the failover chain at and beyond its budget, and the detection-time
inverse checked against the same model are exercised by the gate 3
contract test:
scripts/test_e50_hot_redundant_operation_of_space_network_nodes.py
against
scripts/e50_hot_redundant_operation_of_space_network_nodes_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e50_hot_redundant_operation_of_space_network_nodes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
