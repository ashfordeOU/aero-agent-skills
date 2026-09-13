---
name: e2006-unintended-tether-conductive-paths
description: "Use when trace the stray conduction routes of a tethered system under ECSS-E-ST-20-06C clause 10.2.5: build the conduction graph from the intended tether circuit plus every parasitic route through deployment-hardware, enumerate the closed paths that bypass the intended circuit, categorize each bypass by the hardware it crosses (reel-drum, guide-roller, latch-pin, harness-shield, structure-frame), compute its end-to-end path-resistance and the shunted current fraction from the parallel division against the intended leg, and check each stray route against the isolation-resistance requirement so a bypass through a mechanism is caught before deployment. Trigger: ecss, e-st-20-06c, stray-conduction-path, deployment-hardware-bypass, isolation-resistance, path-resistance, current-division, conduction-graph, tether-circuit-integrity."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-unintended-tether-conductive-paths, stray-conduction-path, deployment-hardware-bypass, isolation-resistance, current-division, conduction-graph, tether-circuit-integrity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Tether — Unintended Conductive Paths (space-systems/ecss/e2006-unintended-tether-conductive-paths)

Use when the task is the stray-conduction verification of
ECSS-E-ST-20-06C clause 10.2.5 -- proving that the current a tethered
system drives stays inside the intended circuit and does not find a
second route home through the deployer, the guide hardware, a harness
shield or the structure frame.

## Domain quick reference

- The object graded here is a graph, not a component. Nodes are the
  electrical nodes of the tethered system (source terminal, tether
  end, deployer chassis, structure frame, return terminal); edges are
  conduction routes between them, each with a resistance. Edges the
  design intends carry the current; every other edge with finite
  resistance is a parasitic route, and a bypass exists whenever the
  parasitic edges close an alternative path between the same two
  terminals as the intended leg.
- A bypass is categorized by the hardware it crosses, because the
  mitigation differs. A reel-drum or guide-roller bypass is a rolling
  or sliding contact that only conducts once the tether is under
  tension; a latch-pin bypass appears at a specific deployment state;
  a harness-shield bypass follows a braid that was bonded at both
  ends; a structure-frame bypass returns through primary structure.
  An unrecognized hardware type is rejected rather than folded into a
  generic route.
- Two numbers grade a bypass. Its path-resistance is the series sum of
  the edges along it. Its shunted fraction comes from the parallel
  division against the intended leg: with the intended resistance Ri
  and the bypass resistance Rb in parallel across the same terminals,
  the fraction of source current taken by the bypass is
  Ri / (Ri + Rb). A high-resistance bypass shunts a negligible
  fraction; a bypass comparable to the intended leg takes roughly half
  the current and is a circuit-integrity failure, not a nuisance.
- The isolation requirement is a floor, not a target. Every parasitic
  edge must measure at least the isolation-resistance minimum on
  record for the interface it crosses; an edge below that floor is a
  finding regardless of how little current the division says it takes,
  because the floor is what keeps the division valid as contacts wear,
  wet or gall. A parasitic edge with no isolation minimum on record is
  an open finding, not a pass.

## Workflow

1. Build the conduction graph: list every node, then every edge with
   its resistance, its intended/parasitic role, and for a parasitic
   edge the hardware it crosses and the isolation minimum required at
   that interface. Reject a duplicate edge, an unknown node reference
   or an unrecognized hardware type before analysis.
2. Enumerate the simple paths between the source terminal and the
   return terminal. The path made only of intended edges is the
   intended leg; every other path that includes at least one parasitic
   edge is a bypass. A graph with no intended leg is rejected as an
   incomplete circuit definition.
3. For each path compute the series path-resistance, then for each
   bypass compute the shunted current fraction Ri / (Ri + Rb) against
   the intended leg resistance.
4. Flag each bypass whose shunted fraction exceeds the allowed
   fraction for the design. Treat an exactly-at-limit fraction as
   compliant: the comparison absorbs the representation error of a
   ratio of sums, and the allowed fraction itself is never widened.
5. Check every parasitic edge against its isolation-resistance
   minimum, and flag an edge whose measured resistance falls below the
   floor or that carries no floor on record.
6. Aggregate the bypass findings and the isolation findings; the
   tethered circuit has integrity only when both lists are empty and
   the enumeration found the intended leg.

## Pitfalls

- Checking components for isolation one at a time and never closing
  the graph. Isolation is a path property: three interfaces that each
  measure acceptably can still form a bypass whose series resistance
  is low enough to shunt real current.
- Assuming a mechanism that is open at stowage stays open. A
  reel-drum, guide-roller or latch-pin conducts at a particular
  deployment state and tension, so the graph is analysed in the state
  where the contact is closed, not the state where it is convenient.
- Reading a small shunted fraction as permission to ignore a
  sub-floor isolation measurement. The floor guards the division
  itself against contact degradation over the mission.
- Bonding a harness shield at both ends without booking the resulting
  edge in the graph. A double-bonded braid is a deliberate conduction
  route and must be graded as one.
- Treating a parasitic edge with no isolation minimum on record as
  compliant by default. An absent requirement is a finding, because
  nothing was ever verified against it.

## Behavior contract (gate 3)

The graph-construction, path-enumeration, path-resistance,
current-division, hardware-categorization and isolation-floor logic is
exercised by the gate 3 contract test:
scripts/test_e2006_unintended_tether_conductive_paths.py against
scripts/e2006_unintended_tether_conductive_paths_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_unintended_tether_conductive_paths.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
