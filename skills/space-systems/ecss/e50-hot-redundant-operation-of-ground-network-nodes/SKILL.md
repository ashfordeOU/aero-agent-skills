---
name: e50-hot-redundant-operation-of-ground-network-nodes
description: "Evaluate a redundant ground network node set against ECSS-E-ST-50C clause 5.8.5, which asks that redundant nodes run hot rather than standby. Separate the redundancy term, the probability at least k of n nodes are up, from the switchover gap; test whether the spare was already running and already in state; charge the gap as the unavailability it costs over a period; and combine the two into the availability the service actually sees. Return the hot node count and the longest gap a target tolerates, each checked back against the same model. Use when reviewing ground node or station redundancy. Trigger: ecss, e-st-50-ground-network, ground-network-node-redundancy, hot-versus-standby-spare, k-of-n-node-availability, switchover-gap-unavailability, ground-node-failover-budget."
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
    clause: 5.8.5
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-ground-network, e50-hot-redundant-operation-of-ground-network-nodes, ground-network-node-redundancy, hot-versus-standby-spare, k-of-n-node-availability, switchover-gap-unavailability, ground-node-failover-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Hot Redundant Operation of Ground Network Nodes (space-systems/ecss/e50-hot-redundant-operation-of-ground-network-nodes)

Use when the nodes of a ground network carry a redundancy requirement per
ECSS-E-ST-50C clause 5.8.5 — deciding whether a design has earned the word
hot, and what the failover it does have actually costs the service.

## Domain quick reference

- The obligation is in one adjective. Redundant is the easy half; hot is
  the half that costs money, because it means the spare is powered,
  configured and already holding the state it needs to serve the next
  request.
- A spare that has to be started, loaded or resynchronised is a standby
  node, whatever the design document calls it. The test is arithmetic,
  not vocabulary: does the failover need start-up time or state recovery
  time, and if either is non-zero the node is not hot.
- Node availability is not service availability. Service availability is
  the probability that at least the required number of nodes are up,
  which is a binomial tail over the node count, and it improves sharply
  with the first spare and slowly after that.
- The switchover gap is a separate, additive loss. It is charged as the
  gap multiplied by how often failover happens, over the period the
  availability is quoted for, and it survives any amount of redundancy.
- That is why a recommendation has to be checked against both terms. A
  node count sized against the redundancy term alone will be short as
  soon as the gap is charged, and the built system misses a target its
  own analysis said it would meet.
- There are two ways to reach an availability target and both belong in
  the report: more hot nodes, or a shorter gap. Which is cheaper depends
  on whether the station is buying hardware or buying detection.

## Workflow

1. Pick out the nodes the clause reaches — the ones that carry the
   control and the operation of the mission's critical functions, not
   every node in the network — and for that set state the node
   availability, the node count, and how many of those nodes the
   service needs at once.
2. Compute the redundancy term as the binomial tail, not as the
   availability of a single node and not as one minus the product of the
   failure rates unless one node really does suffice.
3. Test whether the spare is hot: start-up and state recovery must both
   be zero. Report a non-hot spare as such before anything else, because
   every later number is describing a different architecture.
4. Build the service gap from detection, switchover and, for a spare
   that is not hot, the start-up and state recovery it needs.
5. Charge the gap as an unavailability over the quoted period at the
   expected failover rate, and combine it with the redundancy term.
6. Compare the combined figure with the target using a relative
   tolerance, so a design sized to land exactly on the target is not
   decided by rounding.
7. Where the target is missed, compute both remedies against the same
   combined model: the hot node count that reaches it behind this gap,
   and the longest gap this redundancy tolerates. Report that no count
   reaches it when the gap alone already spends the budget.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.8.5a | 3 |

## Pitfalls

- Calling a spare hot because it is wired in. Powered, configured and in
  state is the bar; a node that boots on demand is a standby node with a
  service gap nobody has budgeted.
- Sizing redundancy against the redundancy term alone. Adding the switch
  gap afterwards moves the answer, and the count that looked sufficient
  is one short.
- Reading a k-of-n set as a simple parallel pair. Two of three is not
  one of two, and the binomial tail is the only expression that gets
  both right.
- Treating an unreachable target as a bigger node count. When the gap
  alone spends more than the target allows, no number of nodes reaches
  it and the honest answer says so.
- Deciding compliance with a bare inequality at the target. Two
  arithmetically identical designs can straddle the bound on different
  machines and the verdict then depends on the build host.
- Quoting an availability with no period. Outage seconds per year and
  outage seconds per pass are different claims about the same fraction.

## Behavior contract (gate 3)

Availability, node-count and gap validation, the binomial redundancy
term, the hot-versus-standby test, the gap charged as unavailability,
the combined service availability, the node-count and maximum-gap
inverses each re-checked against the same model, and the verdict bands
at the exact gap allowance and the exact target are exercised by the
gate 3 contract test:
scripts/test_e50_hot_redundant_operation_of_ground_network_nodes.py
against
scripts/e50_hot_redundant_operation_of_ground_network_nodes_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e50_hot_redundant_operation_of_ground_network_nodes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
