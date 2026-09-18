---
name: e5053-target-logical-address-field
description: "Determine the target logical address octet that opens a packet transfer protocol data unit. Use when an ECSS-E-ST-50-53C clause 5.3.2 encapsulation has to name its destination: categorize a candidate octet as a path-address byte, an assignable logical address, the default address or a reserved value, take the registered address of the destination node, fall back to the default address only where a node has none, prepend the path-address bytes ahead of it, and split a received unit back into path bytes and target address. Refuses a non-integer octet, a value wider than one byte, a path byte holding a logical address and a node absent from the registry. Trigger: ecss, e-st-50-53c, spacewire-target-logical-address-field, spacewire-path-address-prefix, default-logical-address-fallback, logical-address-registry-lookup, address-prefix-decoding."
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
  tags: [ecss, e-st-50-53-packet-transfer-scope, e5053-target-logical-address-field, spacewire-target-logical-address-field, spacewire-path-address-prefix, default-logical-address-fallback, logical-address-registry-lookup, address-prefix-decoding, spacewire-address-octet-category]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Transfer — Target Logical Address Field (space-systems/ecss/e5053-target-logical-address-field)

Use when the task is the destination addressing of ECSS-E-ST-50-53C
clause 5.3.2 -- deciding which octet opens the protocol data unit, and
what a receiver may conclude from the octet it finds there.

## Domain quick reference

- Everything ahead of the protocol identifier is address. Zero or more
  path-address octets are consumed one per router hop, and a single
  target logical address octet survives the network and names the
  destination node.
- The octet space splits four ways: a low range reserved for path
  addressing, an assignable range a node can be given, the default
  address a node answers to before an address is assigned, and a
  reserved value at the top that no node may take.
- A path-address octet in the target field is the classic defect. The
  first router consumes it, the unit continues one octet short, and the
  protocol identifier is then read out of the address of a node that
  was never meant to receive it.
- The default address is legitimate but singular. It reaches whichever
  node has not been given an address of its own, so a network with two
  unaddressed nodes has no way to separate them and the fallback has to
  be recorded as a finding rather than used silently.
- The prefix is ordered, not a set. Path bytes come first in hop order
  and the target address comes last, so a decoder recovers the two by
  walking the leading octets until one leaves the path range.
- The address decision is made from a registry of nodes, not from the
  packet. A node absent from the registry is an error rather than a
  default, because a guess here delivers the unit somewhere.

## Workflow

1. Name the destination node and look it up in the network registry.
   Reject an unknown name rather than defaulting it -- the whole unit is
   delivered on this octet.
2. Take the registered address where the node has one, and refuse a
   registration that sits in the path range or at the reserved value.
3. Where the node carries no registered address, fall back to the
   default address only if the case permits it, and record that at most
   one unaddressed node may sit on the network.
4. Grade the resulting octet: report whether it is assignable, the
   default, a path byte or the reserved value, and whether it can stand
   in the field at all.
5. Build the prefix by writing the path bytes in hop order and the
   target address last, refusing any path byte that a router would keep
   rather than consume.
6. On the receiving side, walk the leading octets while they stay in the
   path range; the first octet that leaves it is the target address, and
   the offset after it is where the protocol identifier begins.

## Pitfalls

- Writing a path-address octet into the target field. It is eaten by the
  first router, every later field shifts by one octet, and the unit is
  then parsed against the wrong field boundaries all the way to the
  packet.
- Treating the default address as a spare address. It is the address of
  whatever node has not been given one, so two unaddressed nodes on one
  network make it ambiguous and the fallback has to be reported.
- Taking the reserved top-of-space value for a valid node address. No
  node may be given it, so a registry entry holding it is a registry
  defect and not a routing choice.
- Assuming the path is empty. A unit that reaches the destination over
  path addressing carries the target address after the path bytes, so a
  decoder that reads octet zero as the target address mis-parses every
  path-routed unit.
- Defaulting an unknown destination node instead of refusing it. A guess
  here does not fail loudly; it delivers a complete, well-formed unit to
  the wrong node.

## Behavior contract (gate 3)

The octet categorization, registry lookup, default-address fallback,
prefix encoding and prefix decoding are exercised by the gate 3 contract
test: scripts/test_e5053_target_logical_address_field.py against
scripts/e5053_target_logical_address_field_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e5053_target_logical_address_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
