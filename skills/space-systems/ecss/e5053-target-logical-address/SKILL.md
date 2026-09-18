---
name: e5053-target-logical-address
description: "Determine the target logical address a sending node writes into a CCSDS packet transfer protocol data unit, and assess a received one, under ECSS-E-ST-50-53C clause 5.1.5: resolve the value from the installation addressing policy, group a received encoding as assignable, the default, a prefix selector or reserved, decide deliver, misrouted or reject at the receiver, and reconcile it with the logical octet the routing prefix ended on. Use when a transfer arrives at a node that does not answer to it. Trigger: ecss, e-st-50-53-spacewire-ccsds-scope, target-logical-address, default-logical-address, logical-address-assignment, misrouted-transfer-discard, logical-addressing-policy."
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
  tags: [ecss, e-st-50-53-spacewire-ccsds-scope, e5053-target-logical-address, target-logical-address, default-logical-address, logical-address-assignment, misrouted-transfer-discard, logical-addressing-policy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Target Logical Address (space-systems/ecss/e5053-target-logical-address)

Use when the task is the target logical address field of the CCSDS packet
transfer protocol data unit of ECSS-E-ST-50-53C clause 5.1.5 — what value the
sending node has to write there, and what a receiving node concludes from the
value it actually finds.

## Domain quick reference

- This field is inside the data unit, not in front of it. No router touches
  it, so what the sender wrote is exactly what the receiver reads. A
  mismatch between the two is a genuine fault and never an artefact of the
  route, which is what makes the field usable as a delivery check.
- The encodings split four ways. Low encodings are held for port selection
  in a routing prefix and cannot name a node. One high encoding is the
  default, meaning the installation does not use logical addressing. The
  highest encoding is reserved. Everything between is assignable to a node.
- The obligation is conditional on the installation, not on the transfer.
  Where logical addressing is used the field carries the target's own
  address; where it is not used the field carries the default. Writing the
  default into a transfer on an installation that does use logical
  addressing throws away the delivery check for that transfer.
- A node may answer to more than one logical address. Delivery is
  membership in the set the node answers to, not equality with a single
  configured value.
- A transfer naming an address this node does not answer to is misrouted,
  which is a different fault from a value that no node could ever hold. The
  first points at a route or address table, the second at the sender.

## Workflow

1. Validate the value against the one octet the field provides; anything
   outside it is a parsing fault upstream.
2. Group the encoding: assignable, the default, a prefix selector encoding
   or the reserved encoding.
3. When writing rather than checking, resolve the value from the
   installation policy: the target's own logical address where logical
   addressing is in use, the default encoding where it is not. Refuse a
   target whose configured address is not an assignable encoding rather
   than emitting it.
4. Validate the set of logical addresses the receiving node answers to, and
   refuse a set containing the default or a prefix selector encoding; those
   can never be delivered to a node.
5. Decide the receiver action: deliver when the value is in the node's set,
   or is the default and the node accepts the default; treat an assignable
   value outside the set as misrouted; reject a prefix selector or reserved
   encoding outright.
6. When the routing prefix ended on a logical octet, compare it with the
   field. Two independent statements of the destination that disagree mean
   one of the two was built from a stale address table.

## Pitfalls

- Comparing this field with the routing prefix as received. The prefix has
  been consumed hop by hop; only its surviving logical octet, if any, is
  comparable, and there may be none at all on a pure path route.
- Using the default encoding as a wildcard. It says logical addressing is
  not in use, not that any node may take the transfer, and a node that
  accepts it while logical addressing is in use will absorb transfers meant
  for its neighbours.
- Assigning a node an address out of the prefix selector range because it
  is free. Those encodings select router ports; a transfer naming one can
  never be delivered to a node and is rejected before any address table is
  consulted.
- Collapsing misrouted and rejected into one outcome. A misrouted transfer
  names a real address and indicates a routing or table error elsewhere; a
  rejected one names an encoding no node could hold and indicts the sender.
- Testing equality against a single configured address on a node that
  answers to several. That discards valid transfers on every multi-address
  node and the loss looks like a link fault.

## Behavior contract (gate 3)

The one-octet validation, four-way grouping, policy-driven resolution, node
address-set validation, the deliver, misrouted and reject decisions and the
routing-prefix cross-check are exercised by the gate 3 contract test:
scripts/test_e5053_target_logical_address.py against
scripts/e5053_target_logical_address_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e5053_target_logical_address.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
